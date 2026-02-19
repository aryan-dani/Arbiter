from google import genai
import os
import json
from backend.nodes import env_loader  # noqa: F401 — loads backend/.env
from backend.state import AgentState

def _extract_failures_section(logs: str) -> str:
    """
    Pull out only the FAILURES block + short test summary from pytest output.
    The LLM must only look at this — not the full log — to prevent wandering.
    """
    lines = logs.splitlines()
    in_section = False
    result = []
    for line in lines:
        # Start capturing at the FAILURES header or short test summary
        if line.startswith("FAILURES") or line.startswith("====== FAILURES") or "_ FAILURES _" in line:
            in_section = True
        if line.startswith("===== short test summary") or "short test summary info" in line:
            in_section = True
        if in_section:
            result.append(line)
    if result:
        return "\n".join(result)
    # Fallback: return the last 80 lines which usually have the error
    return "\n".join(lines[-80:])


def debugger_node(state: AgentState) -> AgentState:
    """
    Analyzes error logs to categorize bugs and identify locations.
    """
    print("Debugger Node Started...")
    
    error_logs = state['error_logs']
    
    # Simple guard if no error logs
    if not error_logs:
        print("No error logs to analyze.")
        return state

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("CRITICAL: GOOGLE_API_KEY not found in environment variables.")
        # Return state without analysis, potentially failing the loop or retrying fruitlessly
        return state

    client = genai.Client(api_key=api_key)
    
    # Provide the list of non-test source files to help AI pick the right one
    repo_path = state.get('repo_path', '')
    source_files = {}
    if repo_path and os.path.exists(repo_path):
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv', '.pytest_cache']]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), repo_path).replace('\\', '/')
                # Allow requirements.txt and package.json to be seen
                if f in ['requirements.txt', 'package.json']:
                    try:
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='replace') as read_f:
                            content = read_f.read()
                            # For config files, line numbers might confuse if not code, but let's be consistent
                            lines = content.splitlines()
                            numbered = "\n".join([f"{i+1}: {line}" for i, line in enumerate(lines)])
                            source_files[rel] = numbered
                    except:
                        pass
                elif f.endswith(('.py', '.js', '.ts')) and not f.startswith('test_') and not f.endswith('_test.py'):
                    try:
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='replace') as read_f:
                            lines = read_f.readlines()
                            numbered = "".join([f"{i+1}: {line}" for i, line in enumerate(lines)])
                            source_files[rel] = numbered
                    except:
                        pass

    # Convert source_files dict to a readable string for the prompt
    source_files_context = ""
    for name, content in source_files.items():
        source_files_context += f"\n--- FILE: {name} ---\n{content}\n"

    # Extract only the FAILURES section — prevents LLM from wandering into unrelated code
    failures_section = _extract_failures_section(error_logs)

    prompt = f"""
    You are an expert Autonomous AI Debugger for the RIFT 2026 Hackathon.
    Your goal is to analyze CI/CD failure logs and identify the ROOT CAUSE source file and line number.

    STRICT ANTI-WANDERING PROTOCOL (Adhere to this above all else):
    1. READ ONLY the FAILURES section below. Do NOT look at files not mentioned in it.
    2. The ONLY file you are allowed to fix is the one in the FAILURES section traceback.
       If aggregator.py is not in the FAILURES section, you MUST ignore aggregator.py entirely.
    3. TRACEBACK GROUNDING: Find the last file in the traceback that is a /src/ file — that is your fix target.
    4. NO-OP GUARD: If the failing test uses `pytest.raises(SomeError)` and the code returns False,
       you MUST raise that specific error — do NOT silently make the logic pass.
    5. LINTING FIXES: Flake8 codes F401, E9, F63, F7, F82 → bug_type = "LINTING".
    6. CLASSIFICATION: Bug Type must be exactly one of: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION.
    7. LINE NUMBERS: Always return the specific failing line (1..N). NEVER return line 0.
    8. NEVER return a test file (test_*.py, *_test.py) as the fix target.

    FAILURES Section (from pytest output):
    {failures_section}

    Source Files (for context — ONLY read files mentioned in the FAILURES section above):
    {source_files_context}

    MAPPING EXAMPLES:
    - test_math.py AssertionError → bug is in src/math_ops.py, not test_math.py
    - F401 'os' imported but unused → File: src/utils.py, Bug: LINTING
    - pytest.raises(SyntaxError) but code returns False → raise SyntaxError in source file
    - ModuleNotFoundError: No module named 'requests' → File: requirements.txt, Bug: IMPORT

    Output strictly as JSON:
    {{
        "file": "src/utils.py",
        "line": 15,
        "bug_type": "LINTING",
        "description": "Remove unused import 'os'"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        analysis = json.loads(response.text)
        if isinstance(analysis, list):
            analysis = analysis[0] if analysis else {}
        
        # Update State
        # We store this temporary analysis to pass to Fixer
        state['current_analysis'] = analysis 
        state['current_step'] = "DEBUG_COMPLETE"
        print(f"Debugger Analysis: {analysis}")
        
    except Exception as e:
        print(f"Debugger Failed: {e}")
        # Fallback or retry logic could go here
        
    return state
