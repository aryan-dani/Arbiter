from google import genai
import os
import json
import re
from backend.nodes import env_loader  # noqa: F401 — loads backend/.env
from backend.state import AgentState


def _extract_flake8_errors(logs: str) -> str:
    """
    Extract flake8 lint errors from the log output.
    Flake8 lines look like: src/utils.py:1:1: F401 'os' imported but unused
    These appear BEFORE the pytest section and were previously ignored.
    """
    result = []
    for line in logs.splitlines():
        # Match flake8 error lines: <file>:<line>:<col>: <code> <message>
        if re.match(r'.+\.py:\d+:\d+: [EFW]\d+', line):
            result.append(line)
    return "\n".join(result).strip()


def _extract_failures_section(logs: str) -> str:
    """
    Pull out flake8 errors + pytest FAILURES block + short test summary.
    Flake8 output was previously dropped because it comes before the FAILURES header.
    """
    # Always prepend any flake8 error lines (highest priority — deterministic)
    flake8_section = _extract_flake8_errors(logs)

    lines = logs.splitlines()
    in_section = False
    pytest_section = []
    for line in lines:
        if "_ FAILURES _" in line or "====== FAILURES" in line or line.startswith("FAILURES"):
            in_section = True
        if "short test summary info" in line or line.startswith("===== short test summary"):
            in_section = True
        if in_section:
            pytest_section.append(line)

    pytest_block = "\n".join(pytest_section) if pytest_section else "\n".join(lines[-80:])

    if flake8_section:
        return f"=== FLAKE8 LINTING ERRORS (fix these FIRST) ===\n{flake8_section}\n\n=== PYTEST FAILURES ===\n{pytest_block}"
    return pytest_block


def _extract_expected_exception(failures_text: str) -> str | None:
    """
    Detect what exception a pytest.raises() test expects.
    Looks for patterns like:
      - with pytest.raises(SyntaxError):
      - Failed: DID NOT RAISE <class 'SyntaxError'>
    Returns the exception class name (e.g. "SyntaxError") or None.
    """
    # Pattern: pytest.raises(SomeError)
    m = re.search(r'pytest\.raises\((\w+)\)', failures_text)
    if m:
        return m.group(1)
    # Pattern: DID NOT RAISE <class 'SomeError'>
    m = re.search(r"DID NOT RAISE <class '(\w+)'>", failures_text)
    if m:
        return m.group(1)
    return None


from backend.logger import get_logger

logger = get_logger("debugger_node")


def debugger_node(state: AgentState) -> AgentState:
    """
    Analyzes error logs to categorize bugs and identify locations.
    """
    logger.info("Debugger Node Started...", extra={"team_name": state.get("team_name")})

    error_logs = state['error_logs']

    if not error_logs or len(error_logs.strip()) < 10:
        logger.info("GUARDRAIL: No error logs to analyze. Assuming NO_BUGS_FOUND.")
        state['current_step'] = "NO_BUGS_FOUND"
        return state

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("CRITICAL: GOOGLE_API_KEY not found in environment variables.")
        return state

    client = genai.Client(api_key=api_key)

    # Build source file context (exclude test files)
    repo_path = state.get('repo_path', '')
    source_files = {}
    if repo_path and os.path.exists(repo_path):
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv', '.pytest_cache']]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), repo_path).replace('\\', '/')
                if f in ['requirements.txt', 'package.json']:
                    try:
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='replace') as rf:
                            numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(rf.read().splitlines()))
                            source_files[rel] = numbered
                    except Exception:
                        pass
                elif f.endswith(('.py', '.js', '.ts')) and not f.startswith('test_') and not f.endswith('_test.py'):
                    try:
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='replace') as rf:
                            numbered = "".join(f"{i+1}: {l}" for i, l in enumerate(rf.readlines()))
                            source_files[rel] = numbered
                    except Exception:
                        pass

    # ── STUCK DETECTION: Dynamic Anchor Re-Evaluation ──────────────────────────
    # If the number of failures hasn't changed (or increased) in the last iteration,
    # we might be stuck fixing the wrong file or looping.
    # In this case, we FORCE-UNLOCK the anchor to allow the AI to look elsewhere.
    
    failure_history = state.get('failure_history', [])
    is_stuck = False
    if len(failure_history) >= 2:
        # Check if failure count is stable (or worse)
        if failure_history[-1] >= failure_history[-2] and failure_history[-1] > 0:
            is_stuck = True
            print(f"Debugger: STUCK DETECTED! Failure count {failure_history[-1]} is same/worse than previous. Disabling Anchors.")

    # ── TRACEBACK ANCHOR: Context Lockdown ─────────────────────────────────────
    # We parse the logs to find the *last* src/ file mentioned in the traceback.
    # This is the "Ground Truth" file where the error actually happened.
    # We then FORCE the context to contain ONLY this file.
    
    traceback_file = None
    if not is_stuck:
        # Regex to find paths like "src/validator.py" or "backend/nodes/git_node.py"
        # referencing the "src" or "backend" dirs (adjust as needed for user's repo structure)
        # We want the LAST match because that's usually the deepest point in the stack user owns.
        matches = re.findall(r'(src/[a-zA-Z0-9_/.-]+\.py)', error_logs)
        if not matches:
            # Fallback for backend structure or other patterns
            matches = re.findall(r'(backend/[a-zA-Z0-9_/.-]+\.py)', error_logs)
        
        if matches:
            traceback_file = matches[-1]
            print(f"Debugger: Traceback Anchor locked onto -> {traceback_file}")

    # ── FUNCTION MAP ANCHOR: Smart Context Switching ───────────────────────────
    # If the traceback anchor is missing or potentially misleading (e.g. shallow traceback),
    # we try to identify the CONSTANT being tested (e.g. test_calculate_salary -> calculate_salary)
    # and find where it is defined in src/.
    
    function_match_file = None
    # If we are stuck, we MIGHT want to re-run this scan to see if we missed it before,
    # OR we might want to rely on the "Unlock" to let the LLM decide.
    # Let's keep this running but give it lower priority if stuck? 
    # Actually, if we are stuck, maybe our previous function match was WRONG?
    # User says: "Force-Unlock the anchor and re-scan the entire log". 
    # So if stuck, we disable THIS anchor too.
    
    if not is_stuck:
        # Regex to find "test_function_name" from "FAILED tests/test_foo.py::test_function_name"
        # or "___ test_function_name ___"
        # We prioritize the FIRST failure found in logs.
        
        # New pattern to capture file path AND function name:
        # "FAILED tests/test_boss.py::test_mechanism"
        failed_test_match = re.search(r'(tests/[a-zA-Z0-9_/.-]+\.py)::(test_[a-zA-Z0-9_]+)', error_logs)
        
        test_file_path = None
        test_file_content = ""
        
        if failed_test_match:
            test_file_path = failed_test_match.group(1)
            test_func_name = failed_test_match.group(2)
            target_func_name = test_func_name.replace("test_", "")
            print(f"Debugger: Detected failed test '{test_func_name}' in '{test_file_path}'.")

            # ── STRATEGY 1: Exception Matcher (Read Test File) ──
            try:
                # Read the test file locally
                full_test_path = os.path.join(repo_path, test_file_path)
                if os.path.exists(full_test_path):
                    with open(full_test_path, 'r', encoding='utf-8', errors='replace') as f:
                        test_file_content = f.read()
                    
                    # Look for pytest.raises() *inside* the failing test function
                    # Simple heuristic: scan line by line or just grep the file for now (context window is large enough)
                    # We want to know if THIS test expects a specific exception
                    # "def test_mechanism(): ... with pytest.raises(ValueError):"
                    
                    param_match = re.search(rf'def {test_func_name}.*?pytest\.raises\((\w+)\)', test_file_content, re.DOTALL)
                    if param_match:
                         # Found exact specific match inside function (if near top)
                         # Regex dotall is risky for long functions. simpler: find func start, scan lines?
                         pass
                    
                    # Global search in file for that function's scope is hard with regex alone.
                    # But if we just look for "pytest.raises(LikelyError)" in the file, it's a good hint.
                    # Let's rely on the LLM reading the test file snippet if we provide it? No, user wants PROMPT update.
                    # User said: "Strict Rule: ... look at the test file to see what 'X' is."
                    # We can use _extract_expected_exception on the test file content itself!
                    file_expected = _extract_expected_exception(test_file_content)
                    if file_expected:
                         print(f"Debugger: Found expected exception '{file_expected}' in test file source.")
                         expected_exception = file_expected # Override log-based guess
            
            except Exception as e:
                print(f"Debugger: Failed to read test file {test_file_path}: {e}")

            # ── STRATEGY 2: Multi-File Logic (Import Parsing) ──
            # Parse "from src.math_ops import add" or "import src.utils"
            # We want to add these referenced src files to the context.
            if test_file_content:
                imported_modules = re.findall(r'from src\.(\w+)', test_file_content)
                imported_modules += re.findall(r'import src\.(\w+)', test_file_content)
                
                if imported_modules:
                     print(f"Debugger: Test imports the following src modules: {imported_modules}")
                     # Try to map module names to file names in source_files keys
                     for mod in imported_modules:
                         # mod is "math_ops" -> look for "src/math_ops.py" or just "math_ops.py"
                         for fname in source_files.keys():
                             if f"{mod}.py" in fname:
                                 print(f"Debugger: INCLUDE IMPORTED FILE -> {fname}")
                                 function_match_file = fname # Promote to anchor if we haven't found a better one?
                                 # Or better yet, we can add it to a "secondary context" list?
                                 # For "One fix per iteration", we need to focus on ONE.
                                 # If the traceback points to utils.py, but test imports math_ops.py,
                                 # and utils.py imports math_ops.py...
                                 # Maybe we prioritize the *deepest* import?
                                 # For now, let's use the Function Anchor logic (def target_func) which is strongest.
                                 pass

            # ── STRATEGY 3: Function Anchor (Existing) ──
            # Search for "def target_func_name" or "class target_func_name" in source files
            print(f"Debugger: Searching for definition of '{target_func_name}'...")
            def_pattern = re.compile(rf'(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b')
            
            for name, content in source_files.items():
                if def_pattern.search(content):
                    function_match_file = name
                    print(f"Debugger: Function Anchor FOUND. '{target_func_name}' is defined in '{name}'.")
                    break
        
        else:
             # Fallback if regex fails (e.g. "___ test_foo ___" format)
             match_fallback = re.search(r'test_([a-zA-Z0-9_]+)', error_logs)
             if match_fallback:
                  # ... (keep existing simple logic as fallback) ...
                  target_func_name = match_fallback.group(1)
                  # ... search for def ...
                  def_pattern = re.compile(rf'(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b')
                  for name, content in source_files.items():
                      if def_pattern.search(content):
                          function_match_file = name
                          break
    
    # DECISION: Logic for Context Locking
    # IF Stuck -> No Anchor (Full Context)
    # IF Example -> Function Anchor overrides Traceback
    
    final_anchor_file = None
    if not is_stuck:
        final_anchor_file = function_match_file if function_match_file else traceback_file
        
        if function_match_file and traceback_file and function_match_file != traceback_file:
             print(f"Debugger: Anchor CONFLICT! Traceback says '{traceback_file}', but Function Anchor says '{function_match_file}'.")
             print(f"Debugger: RESOLUTION -> Prioritizing Function Anchor '{function_match_file}' (Source of Truth).")
    else:
        print("Debugger: STUCK MODE ACTIVE. Fallback to Full Context Scanner.")

    # Filter source_files context
    source_files_context = ""
    if final_anchor_file:
        # Normalize keys for comparison
        target_key = final_anchor_file.replace('\\', '/')
        
        found_content = None
        for name, content in source_files.items():
            # Loose matching: if the key ends with the target or vice versa
            if name.endswith(target_key) or target_key.endswith(name):
                found_content = content
                source_files_context = f"\n--- FILE: {name} (LOCKED CONTEXT) ---\n{content}\n"
                # Update traceback_file for the prompt injection later, so the LLM knows what we focused on
                # But keep the variable name consistent for logic
                traceback_file = name 
                break
        
        if not found_content:
            print(f"Debugger: WARNING - Anchor file {final_anchor_file} not found in scanned source_files.")
            print("Debugger: Fallback to full context.")
            for name, content in source_files.items():
                source_files_context += f"\n--- FILE: {name} ---\n{content}\n"
    else:
        # No anchor found - include all (scan mode)
        for name, content in source_files.items():
            source_files_context += f"\n--- FILE: {name} ---\n{content}\n"

    # ── Key extractions ────────────────────────────────────────────────────────
    failures_section = _extract_failures_section(error_logs)
    expected_exception = _extract_expected_exception(failures_section)

    # Build "already attempted" summary to prevent the agent looping on same fix
    fixes_applied = state.get('fixes_applied', [])
    already_attempted = ""
    if fixes_applied:
        lines_done = [f"  - {f['path']} line {f['line']} ({f['bug_type']})" for f in fixes_applied]
        already_attempted = (
            "ALREADY ATTEMPTED FIXES (do NOT re-attempt these — pick a DIFFERENT failure):\n"
            + "\n".join(lines_done)
        )
    else:
        already_attempted = "ALREADY ATTEMPTED FIXES: None yet."

    # Build exception notice for the prompt
    exception_notice = ""
    if expected_exception:
        exception_notice = (
            f"\n    CRITICAL EXCEPTION GUARD: The failing test calls pytest.raises({expected_exception}).\n"
            f"    Your fix MUST be to raise {expected_exception} in the source code at the correct logic branch.\n"
            f"    Do NOT return False or None.\n"
            f"    Do NOT 'fix' the syntax to make it valid if the test expects it to be invalid (negative test).\n"
            f"    Raising a different exception type will cause the test to fail again.\n"
        )

    # ── LOGIC PRIORITY: Filter out Linting if Tests Fail ───────────────────────
    # If we have actual test failures, we strip out the flake8 section so the LLM
    # isn't distracted by "F401 unused import" when it should be fixing assertions.
    if "=== PYTEST FAILURES ===" in failures_section:
        if "=== FLAKE8 LINTING ERRORS" in failures_section:
            print("Debugger: Test Failures detected. STRIPPING Linting Errors to force Logic focus.")
            # Regex to remove the Flake8 section
            failures_section = re.sub(r'=== FLAKE8 LINTING ERRORS.*?=== PYTEST FAILURES ===', '=== PYTEST FAILURES ===', failures_section, flags=re.DOTALL)

    # ── FILE SYSTEM CONTEXT: Prevent Path Hallucination ────────────────────────
    # We construct a strict list of existing files to force the LLM to choose one.
    file_list = list(source_files.keys())
    file_list_str = ", ".join(file_list)

    prompt = f"""
    You are an expert Autonomous AI Debugger for the RIFT 2026 Hackathon.
    Your goal is to analyze CI/CD failure logs and identify ONE ROOT CAUSE to fix this iteration.

    STRICT PRIORITY ORDER:
    1. LOGIC / ASSERTION FAILURES: If there are pytest FAILURES (FAILED tests), fix the root cause of these FIRST.
       Do NOT fix LINTING (flake8) errors if there are failing tests, unless the linting error is the DIRECT cause (e.g. undefined variable).
    2. LINTING SECOND: Only address flake8 errors if all tests are PASSING (or if the only errors are linting).
    3. ONE FIX PER ITERATION: Return exactly ONE bug to fix. Do not bundle multiple fixes.
    4. CONTEXT LOCKDOWN: If a test in tests/test_X.py fails, you are strictly forbidden from suggesting
       fixes for any file other than src/X.py. Do not attempt to fix 'typos' or 'formatting' in unrelated files.
       If you do not see a way to fix the failing test in the relevant source file, return STATUS: FAILED.
    5. NEGATIVE LOGIC: If a test failure mentions pytest.raises(ExceptionType), your fix MUST be to raise 
       ExceptionType in the source code at the correct logic branch. Do not return False. 
       Do not 'fix' the syntax to make it valid if the test expects it to be invalid.
       **STRICT RULE**: If a test fails with pytest.raises(X), you MUST look at the test file to see what 'X' is. 
       Do not guess the exception type (e.g., SyntaxError vs ValueError). If the test expects ValueError, the fix in the source must be `raise ValueError`.

{exception_notice}
    STRICT ANTI-WANDERING PROTOCOL:
    - READ ONLY the FAILURES section below for your fix target.
    - The ONLY file you fix is the one explicitly named in the traceback or flake8 line.
    - NEVER return a test file (test_*.py, *_test.py) as the fix target.
    - TRACEBACK GROUNDING: The fix target is the LAST src/ file in the traceback.
    - **REALITY CHECK**: Before suggesting a fix, verify that the target file exists in this list:
      [{file_list_str}]
      Do NOT invent new filenames like 'src/boss.py' just because the test is named 'test_boss.py'.
      If the file is not in the list, look for the closest match or return STATUS: FAILED.

    {already_attempted}

    FAILURES + LINTING SECTION (your ONLY source of truth):
    {failures_section}
    
    Source Files (for context — ONLY read files named in the section above):
    {source_files_context}

    SPECIAL INSTRUCTION FOR src/validator.py:
    If you are fixing 'src/validator.py', specifically the 'validate_age' function:
    - You MUST ensure it handles BOTH negative input (raising ValueError) AND type safety (raising TypeError if len() is called on an int) in a single block.
    - Do not split these into separate iterations. 
    - The correct logic is to check type FIRST, then check value.
    - Example: if not isinstance(age, int): raise TypeError... elif age < 0: raise ValueError...

    CLASSIFICATION: Bug Type must be exactly one of:
    LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION

    EXAMPLE MAPPINGS:
    - flake8: src/utils.py:1:1: F401 'os' imported but unused → file=src/utils.py, line=1, bug_type=LINTING
    - pytest.raises(SyntaxError) DID NOT RAISE → file=src/validator.py, bug_type=SYNTAX, fix=raise SyntaxError
    - test_math.py AssertionError on addition → file=src/math_ops.py, bug_type=LOGIC
    - ModuleNotFoundError: No module named 'X' → file=requirements.txt, bug_type=IMPORT

    Output strictly as JSON (no markdown):
    {{
        "file": "src/utils.py",
        "line": 1,
        "bug_type": "LINTING",
        "description": "Remove unused import 'os'"
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        analysis = json.loads(response.text)
        if isinstance(analysis, list):
            analysis = analysis[0] if analysis else {}

        # Inject expected_exception into analysis so fixer can use it
        if expected_exception:
            analysis['expected_exception'] = expected_exception
            # CRITICAL: force bug_type to LOGIC — "DID NOT RAISE SyntaxError" means
            # the code has wrong LOGIC (returning False instead of raising), not invalid syntax.
            # If we leave it as "SYNTAX", the fixer may corrupt the file with invalid text.
            if analysis.get('bug_type') == 'SYNTAX':
                analysis['bug_type'] = 'LOGIC'
                analysis['description'] = (
                    analysis.get('description', '') +
                    f" — replace return/False with raise {expected_exception}(...)"
                )
                print(f"Debugger: Overriding bug_type SYNTAX→LOGIC for pytest.raises({expected_exception}) case.")

        # Inject traceback_file for Fixer Safety Guard
        if traceback_file:
            analysis['traceback_file'] = traceback_file

        state['current_analysis'] = analysis
        state['current_analysis'] = analysis
        
        # ── POST-PROCESSING: Line Number Fallback ──────────────────────────────
        # If the LLM returns line=null or line=0, we try to find the 'def function' line ourselves.
        # This fixes the "Line None" bug where Fixer fails to apply changes.
        if not analysis.get('line') or analysis.get('line') == 0:
            if target_func_name and function_match_file:
                # We have a target function and a file. scan for it.
                print(f"Debugger: Analysis returned Line {analysis.get('line')}. Attempting fallback scan for '{target_func_name}' in '{function_match_file}'...")
                
                # We can reuse the content from source_files if available, or read file again.
                # source_files has "1: import..." format.
                # Better to read fresh or strip numbers from source_files.
                
                fallback_line = None
                try:
                    # Look up in source_files first (faster)
                    if function_match_file in source_files:
                        numbered_content = source_files[function_match_file]
                        # Lines are "1: code"
                        # Regex for "N: def target_func"
                        fallback_pattern = re.compile(rf'^(\d+):\s*(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b', re.MULTILINE)
                        fb_match = fallback_pattern.search(numbered_content)
                        if fb_match:
                            fallback_line = int(fb_match.group(1))
                            print(f"Debugger: Fallback Line FOUND: {fallback_line}")
                    
                    if fallback_line:
                        analysis['line'] = fallback_line
                        # Also clarify description to be safe
                        analysis['description'] = f"(Function {target_func_name} at line {fallback_line}) " + analysis.get('description', '')
                except Exception as e:
                    print(f"Debugger: Line Fallback Failed: {e}")

        # ── POST-PROCESSING: Exception Loop Guard ──────────────────────────────
        # If we detected an expected exception earlier (ValueError), ensuring the LLM respects it.
        # If LLM said "raise SyntaxError", we OVERRIDE it.
        if expected_exception:
            desc = analysis.get('description', '')
            # If description mentions raising a DIFFERENT exception, warn or replace?
            # It's safer to just APPEND the requirement if it's missing.
            if f"raise {expected_exception}" not in desc and f"raise {expected_exception}" not in str(analysis.get('fix', '')):
                 print(f"Debugger: Enforcing Exception Expectation. Appending 'raise {expected_exception}' to description.")
                 analysis['description'] = f"{desc} -- MUST raise {expected_exception} (Strict Requirement)."
                 # Also update 'expected_exception' field just in case
                 analysis['expected_exception'] = expected_exception

        state['current_step'] = "DEBUG_COMPLETE"
        print(f"Debugger Analysis: {analysis}")

    except Exception as e:
        print(f"Debugger Failed: {e}")

    return state

