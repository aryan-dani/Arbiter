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

    # ── TRACEBACK ANCHOR: Context Lockdown ─────────────────────────────────────
    # We parse the logs to find the *last* src/ file mentioned in the traceback.
    # This is the "Ground Truth" file where the error actually happened.
    # We then FORCE the context to contain ONLY this file.
    
    traceback_file = None
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
    
    # Filter source_files context
    source_files_context = ""
    if traceback_file:
        # We might have the file in source_files with a slightly different relative path
        # e.g. "src/validator.py" vs "validator.py" if repo_path root is src (unlikely)
        # or "validator.py" if os.walk returns relative.
        # Let's check matching keys.
        
        # Normalize keys for comparison
        target_key = traceback_file.replace('\\', '/')
        
        found_content = None
        for name, content in source_files.items():
            # Loose matching: if the key ends with the target or vice versa
            if name.endswith(target_key) or target_key.endswith(name):
                found_content = content
                source_files_context = f"\n--- FILE: {name} (LOCKED CONTEXT) ---\n{content}\n"
                break
        
        if not found_content:
            print(f"Debugger: WARNING - Traceback file {traceback_file} not found in scanned source_files.")
            # Fallback: include all source files if we can't map it? 
            # OR better: iterate and include all, trusting the LLM?
            # User wants STRICT ISOLATION. If we can't find it, maybe we fail?
            # Let's fallback to standard "include all" but warn.
            print("Debugger: Fallback to full context.")
            for name, content in source_files.items():
                source_files_context += f"\n--- FILE: {name} ---\n{content}\n"
    else:
        # No traceback file found - include all (scan mode)
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

    prompt = f"""
    You are an expert Autonomous AI Debugger for the RIFT 2026 Hackathon.
    Your goal is to analyze CI/CD failure logs and identify ONE ROOT CAUSE to fix this iteration.

    STRICT PRIORITY ORDER:
    1. LINTING FIRST: If the logs contain flake8 errors (F401, F811, E9, F63, F7, F82), fix the
       linting error BEFORE any pytest failure. Linting errors are deterministic and fast to fix.
    2. PYTEST SECOND: Only address a pytest failure if there are no flake8 errors remaining.
    3. ONE FIX PER ITERATION: Return exactly ONE bug to fix. Do not bundle multiple fixes.
    4. CONTEXT LOCKDOWN: If a test in tests/test_X.py fails, you are strictly forbidden from suggesting
       fixes for any file other than src/X.py. Do not attempt to fix 'typos' or 'formatting' in unrelated files.
       If you do not see a way to fix the failing test in the relevant source file, return STATUS: FAILED.
    5. NEGATIVE LOGIC: If a test failure mentions pytest.raises(ExceptionType), your fix MUST be to raise 
       ExceptionType in the source code at the correct logic branch. Do not return False. 
       Do not 'fix' the syntax to make it valid if the test expects it to be invalid.

{exception_notice}
    STRICT ANTI-WANDERING PROTOCOL:
    - READ ONLY the FAILURES section below for your fix target.
    - The ONLY file you fix is the one explicitly named in the traceback or flake8 line.
    - NEVER return a test file (test_*.py, *_test.py) as the fix target.
    - TRACEBACK GROUNDING: The fix target is the LAST src/ file in the traceback.

    {already_attempted}

    FAILURES + LINTING SECTION (your ONLY source of truth):
    {failures_section}

    Source Files (for context — ONLY read files named in the section above):
    {source_files_context}

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
        state['current_step'] = "DEBUG_COMPLETE"
        print(f"Debugger Analysis: {analysis}")

    except Exception as e:
        print(f"Debugger Failed: {e}")

    return state

