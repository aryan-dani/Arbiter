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


def _extract_expected_exceptions(failures_text: str) -> list[str]:
    """
    Detect what exceptions pytest.raises() tests expect.
    Returns a list of unique exception class names (e.g. ["ValueError", "TypeError"]).
    """
    exceptions = set()
    # Pattern: pytest.raises(SomeError)
    matches_raises = re.findall(r'pytest\.raises\((\w+)\)', failures_text)
    exceptions.update(matches_raises)
    
    # Pattern: DID NOT RAISE <class 'SomeError'>
    matches_did_not_raise = re.findall(r"DID NOT RAISE <class '(\w+)'>", failures_text)
    exceptions.update(matches_did_not_raise)
    
    return sorted(list(exceptions))


from backend.logger import get_logger

logger = get_logger("debugger_node")


def debugger_node(state: AgentState) -> AgentState:
    """
    Analyzes error logs to categorize bugs and identify locations.
    """
    print("Debugger Node Started...")
    
    # ── VARIABLE SAFETY: Initialize local vars to prevent UnboundLocalError ──
    import_source_file = None
    import_source_files = []
    function_match_file = None
    test_file_path = None
    traceback_file = None
    target_func_name = None
    expected_exception = None
    source_files_context = ""
    
    try:
        error_logs = state['error_logs']

        if not error_logs or len(error_logs.strip()) < 10:
            print("GUARDRAIL: No error logs to analyze. Assuming NO_BUGS_FOUND.")
            state['current_step'] = "NO_BUGS_FOUND"
            return state

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("CRITICAL: GOOGLE_API_KEY not found in environment variables.")
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
        failure_history = state.get('failure_history', [])
        is_stuck = False
        if len(failure_history) >= 2:
            if failure_history[-1] >= failure_history[-2] and failure_history[-1] > 0:
                is_stuck = True
                print(f"Debugger: STUCK DETECTED! Failure count {failure_history[-1]} is same/worse than previous. Disabling Anchors.")

        # ── TRACEBACK ANCHOR: Context Lockdown ─────────────────────────────────────
        if not is_stuck:
            matches = re.findall(r'(src/[a-zA-Z0-9_/.-]+\.py)', error_logs)
            if not matches:
                matches = re.findall(r'(backend/[a-zA-Z0-9_/.-]+\.py)', error_logs)
            
            if matches:
                traceback_file = matches[-1]
                print(f"Debugger: Traceback Anchor locked onto -> {traceback_file}")

        # ── FUNCTION MAP ANCHOR: Smart Context Switching ───────────────────────────
        if not is_stuck:
            failed_test_match = re.search(r'(tests/[a-zA-Z0-9_/.-]+\.py)::(test_[a-zA-Z0-9_]+)', error_logs)
            test_file_content = ""
            
            if failed_test_match:
                test_file_path = failed_test_match.group(1)
                test_func_name = failed_test_match.group(2)
                target_func_name = test_func_name.replace("test_", "")
                print(f"Debugger: Detected failed test '{test_func_name}' in '{test_file_path}'.")

                # ── STRATEGY 1: Exception Matcher (Read Test File) ──
                try:
                    full_test_path = os.path.join(repo_path, test_file_path)
                    if os.path.exists(full_test_path):
                        with open(full_test_path, 'r', encoding='utf-8', errors='replace') as f:
                            test_file_content = f.read()
                        
                        file_expected_list = _extract_expected_exceptions(test_file_content)
                        if file_expected_list:
                             print(f"Debugger: Found expected exceptions '{file_expected_list}' in test file source.")
                             expected_exception = file_expected_list[0]
                except Exception as e:
                    print(f"Debugger: Failed to read test file {test_file_path}: {e}")

                # ── STRATEGY 2: Dependency Graph (Import Parsing) ──
                if test_file_content:
                    imported_modules = re.findall(r'from src\.([a-zA-Z0-9_]+)', test_file_content)
                    imported_modules += re.findall(r'import src\.([a-zA-Z0-9_]+)', test_file_content)
                    
                    if imported_modules:
                        print(f"Debugger: Dependency Graph - Test imports from src: {imported_modules}")
                        for mod in set(imported_modules):
                            for fname in source_files.keys():
                                if f"{mod}.py" in fname:
                                    import_source_file = fname
                                    import_source_files.append(fname)
                                    break
                        if import_source_files:
                            print(f"Debugger: Identified related source files: {import_source_files}")

                # ── STRATEGY 3: Function Anchor ──
                print(f"Debugger: Searching for definition of '{target_func_name}'...")
                def_pattern = re.compile(rf'(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b')
                for name, content in source_files.items():
                    if def_pattern.search(content):
                        function_match_file = name
                        print(f"Debugger: Function Anchor FOUND. '{target_func_name}' is defined in '{name}'.")
                        break
                
                # ── HEURISTIC PRIORITY & CONFLICT RESOLUTION ──────────────────────────
                if import_source_file:
                     if function_match_file and function_match_file != import_source_file:
                          print(f"Debugger: Dependency Conflict! Prioritizing Import Source '{import_source_file}' over Function Match.")
                          function_match_file = import_source_file
        
        else:
             # Fallback if regex fails (e.g. "___ test_foo ___" format)
             match_fallback = re.search(r'test_([a-zA-Z0-9_]+)', error_logs)
             if match_fallback:
                  target_func_name = match_fallback.group(1)
                  def_pattern = re.compile(rf'(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b')
                  for name, content in source_files.items():
                      if def_pattern.search(content):
                          function_match_file = name
                          break
    
        # ── ANCHOR RESOLUTION ──────────────────────────────────────────────────
        final_anchor_file = None

        if not is_stuck:
            if import_source_file:
                final_anchor_file = import_source_file
                if traceback_file and traceback_file != import_source_file:
                    print(f"Debugger: Anchor Conflict! Traceback says '{traceback_file}' but Import Source says '{import_source_file}'.")
                    print(f"Debugger: RESOLUTION -> Anchor = Import Source '{import_source_file}'.")
            else:
                final_anchor_file = function_match_file if function_match_file else traceback_file
        else:
            print("Debugger: STUCK MODE ACTIVE. Fallback to Full Context Scanner.")

        # Filter source_files context
        source_files_context = ""
        if final_anchor_file:
            target_key = final_anchor_file.replace('\\', '/')
            found_content = None
            for name, content in source_files.items():
                if name.endswith(target_key) or target_key.endswith(name):
                    found_content = content
                    source_files_context = f"\n--- FILE: {name} (LOCKED CONTEXT) ---\n{content}\n"
                    traceback_file = name 
                    break
            
            if not found_content:
                print(f"Debugger: WARNING - Anchor file {final_anchor_file} not found in scanned source_files.")
                for name, content in source_files.items():
                    source_files_context += f"\n--- FILE: {name} ---\n{content}\n"
        else:
            for name, content in source_files.items():
                source_files_context += f"\n--- FILE: {name} ---\n{content}\n"

        # ── Key extractions ────────────────────────────────────────────────────────
        failures_section = _extract_failures_section(error_logs)
        expected_exceptions = _extract_expected_exceptions(failures_section)

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

        exception_notice = ""
        if expected_exceptions:
            ex_str = ", ".join(expected_exceptions)
            exception_notice = (
                f"\n    CRITICAL EXCEPTION GUARD: The failing tests call pytest.raises() for: {ex_str}.\n"
                f"    Your fix MUST be to raise these specific exceptions in the source code at the correct logic branches.\n"
                f"    Do NOT return False or None.\n"
                f"    If multiple exceptions are expected (e.g. ValueError AND TypeError), you MUST handle all conditions.\n"
            )

        # No longer stripping linting errors. The Sovereign Prompt handles F401.

        file_list = list(source_files.keys())
        file_list_str = ", ".join(file_list)

        prompt = f"""
    You are "The Arbiter" — an Elite Autonomous DevOps Engineer for the RIFT 2026 Hackathon.
    Context: You are running on a Windows host but testing in a Linux container.

    YOUR MISSION:
    Analyze CI/CD failure logs and identify the ROOT CAUSE(S) of the failure.

    *** ARBITER FINAL SWEEP SOVEREIGN PROMPT ***
    Role: Senior Principal DevOps Architect.
    
    CRITICAL PRIORITY ORDER:

    1. WORKSPACE INTEGRITY (Git Conflict Trap):
       - Check specifically for '<<<<<<< HEAD' or '=======' in any source file.
       - If found, your FIRST and ONLY task is to delete all Git markers and restore clean Python syntax.
       - Do NOT attempt logic fixes until syntax is clean.

    2. SYNTAX/LINTING BLOCKERS:
       - Fix 'SyntaxError' or 'IndentationError' in any file.
       - Fix 'F401' (Unused Import) errors:
         - Remove `import os`, `import sys` or other unused imports if flagged by flake8.
       - Force 4-space indentation globally.

    3. ANTI-HALLUCINATION & ANCHOR MAPPING:
       - Strict Rule: Only target files found in 'Discovered Source Files'.
       - Do NOT suggest fixes for files that do not exist (e.g. if `test_boss.py` exists but `src/boss.py` does not, check imports).
       - Import Fix: If a test fails with `ImportError`, ensure the imported module exists and has a properly defined `main()` or `__init__.py`.

    4. GHOST FAILURE SWEEP (FINAL 110 PUSH):
       - TARGET OUTLIERS: Focus heavily on any test files in `tests/`.
       - IGNORE PASSED: Likely passing files do not need fixes unless they have syntax errors.
       - STRING ACCURACY: 
         - If a test fails due to a string mismatch (e.g. `AssertionError: 'A' != 'B'`), trust the test's expectation.
         - For example, if `test_utils.py` fails on `useful_function`, ensure the return value EXACTLY matches the test expectation (including punctuation).

    5. GREEDY EXCEPTION HARDENING (The "Boss" Level):
       - If a test fails due to validation logic (e.g., `validate_age` or similar):
         - Map the failure to the corresponding source file.
         - You MUST implement a unified `if/elif` block to handle ALL expected exceptions.
           - raise `TypeError` if input is the wrong type.
           - raise `ValueError` if input is invalid (e.g. negative).
           - raise `SyntaxError` or others if strictly required by the test.

    6. CODE LOGIC:
       - If a test fails due to incorrect logic (e.g. `AssertionError: 5 != 6`), fix the math or logic in the source file.
       - Example: Change `*` to `+` if the test expects addition.
    *****************************************

    1. GREEDY FAILURE ANALYSIS:
       - Do NOT focus on a single failure. Scan the ENTIRE pytest log.
       - If multiple tests fail in the same file, summarize ALL of them.
       - If src/validator.py has multiple failing tests (e.g., one expecting ValueError, one expecting TypeError), 
         you MUST flag this so the fixer implements a unified if/elif/else block.

    2. ANCHOR PRIORITY:
       - If a Traceback Anchor Conflict is detected, prioritize the Import Source (the file the test actually imports) over the traceback utility file.
       - CRITICAL: Do NOT assume a source file exists just because a test file is named after it (e.g., test_boss.py does NOT mean src/boss.py exists). 
       - You MUST only suggest fixes for files identified in the 'Discovered Source Files' list or files explicitly imported by the test. 
       - If the bug is in a function imported from src/app.py or src/math_ops.py, target those files only.

    3. OS-AGNOSTIC INTEGRITY:
       - Assume the workspace is corrupted if you see Git markers (<<<<<<< HEAD). 
       - Your first priority is to delete markers and restore valid Python syntax.

    4. STRICT PRIORITY ORDER:
       - LOGIC / ASSERTION FAILURES: If there are pytest FAILURES (FAILED tests), fix the root cause of these FIRST.
       - NEGATIVE LOGIC: If a test failure mentions pytest.raises(ExceptionType), your fix MUST be to raise ExceptionType in the source code.
       - CONTEXT LOCKDOWN: If a test in tests/test_X.py fails, prefer fixing src/X.py. 
         HOWEVER, if src/X.py does not exist, check the test file's imports and fix the actual source file (e.g. src/app.py).

    {exception_notice}
    
    {already_attempted}

    FAILURES + LINTING SECTION (your ONLY source of truth):
    {failures_section}
    
    Source Files (for context):
    {source_files_context}

    SPECIAL INSTRUCTION FOR src/validator.py (if applicable):
    - You MUST ensure it handles BOTH negative input (raising ValueError) AND type safety (raising TypeError if len() is called on an int) in a single block.
    - Example: if not isinstance(age, int): raise TypeError... elif age < 0: raise ValueError...

    CLASSIFICATION: Bug Type must be exactly one of:
    LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION, MARKER_CLEANUP

    Output strictly as JSON:
    {{
        "file": "src/utils.py",
        "line": 1,
        "bug_type": "LINTING",
        "description": "Remove unused import 'os'"
    }}
    """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        analysis = json.loads(response.text)
        if isinstance(analysis, list):
            analysis = analysis[0] if analysis else {}

        if expected_exceptions:
            analysis['expected_exceptions'] = expected_exceptions
            if analysis.get('bug_type') == 'SYNTAX':
                analysis['bug_type'] = 'LOGIC'

        if traceback_file:
            analysis['traceback_file'] = traceback_file

        state['current_analysis'] = analysis

        # Line Number Fallback
        if not analysis.get('line') or analysis.get('line') == 0:
            if target_func_name and function_match_file:
                fallback_line = None
                if function_match_file in source_files:
                    numbered_content = source_files[function_match_file]
                    fallback_pattern = re.compile(rf'^(\d+):\s*(async\s+)?(def|class)\s+{re.escape(target_func_name)}\b', re.MULTILINE)
                    fb_match = fallback_pattern.search(numbered_content)
                    if fb_match:
                        fallback_line = int(fb_match.group(1))
                        analysis['line'] = fallback_line

        state['current_step'] = "DEBUG_COMPLETE"
        print(f"Debugger Analysis: {analysis}")

    except Exception as e:
        import traceback
        print(f"Debugger Failed: {e}\n{traceback.format_exc()}")

    return state
