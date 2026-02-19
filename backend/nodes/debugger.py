from google import genai
import os
import json
from backend.nodes import env_loader  # noqa: F401 — loads backend/.env
from backend.state import AgentState

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

    prompt = f"""
    You are an expert Autonomous AI Debugger for the RIFT 2026 Hackathon.
    Your goal is to analyze CI/CD failure logs and identify the ROOT CAUSE source file and line number.

    STRICT REASONING PROTOCOL (Adhere to this above all else):
    1. PRIORITIZE TOOL OUTPUT: The logs contain output from 'flake8' and 'pytest'. Use it.
    2. LINTING FIXES: If you see error codes like F401, E9, F63, F7, F82, you MUST categorize this as a 'LINTING' bug.
       - Example: 'os' imported but unused -> File: src/utils.py, Bug: LINTING, Fix: Remove unused import.
    3. DEPENDENCY GUARD: Do NOT suggest adding libraries to requirements.txt unless you see a 'ModuleNotFoundError' or 'ImportError' in the logs.
    4. NO-OP DETECTION: If a fix was already attempted for this line/file, try a different approach.
    5. CLASSIFICATION: Bug Type must be exactly one of: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION.
    6. LINE NUMBERS: You have the file content with line numbers. You MUST identify the specific line number (1 to N). NEVER return line 0.

    Error Logs:
    {error_logs}

    Source Files Content (with line numbers):
    {source_files_context}

    CRITICAL RULES:
    1. NEVER return a test file (test_*.py, *_test.py) as the "file" to fix.
       Test files show WHERE the failure was detected, not WHERE the bug lives.
    2. Always trace AssertionErrors and failures back to the SOURCE file being tested.
       Example: if test_bank.py line 13 fails with wrong balance, the bug is in bank.py deposit().
    3. Pick the file from the "Source Files Content" list above.
    4. MAPPING EXAMPLES:
       - F401 'os' imported but unused -> File: src/utils.py, Bug: LINTING, Fix: Remove unused import 'os'
       - test_math.py fails assertion -> File: src/math_ops.py, Bug: LOGIC, Fix: Correct the calculation
       - ModuleNotFoundError: No module named 'requests' -> File: requirements.txt, Bug: IMPORT, Fix: Add requests

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
