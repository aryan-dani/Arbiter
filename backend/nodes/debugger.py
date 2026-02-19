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
    source_files = []
    if repo_path and os.path.exists(repo_path):
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv']]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), repo_path).replace('\\', '/')
                if f.endswith(('.py', '.js', '.ts')) and not f.startswith('test_') and not f.endswith('_test.py'):
                    source_files.append(rel)

    prompt = f"""
    You are an expert Python/Node.js debugger analyzing CI/CD pipeline failures.

    Error Logs:
    {error_logs}

    Source files available in the repository (NOT test files):
    {source_files}

    CRITICAL RULES:
    1. NEVER return a test file (test_*.py, *_test.py) as the "file" to fix.
       Test files show WHERE the failure was detected, not WHERE the bug lives.
    2. Always trace AssertionErrors and failures back to the SOURCE file being tested.
       Example: if test_bank.py line 13 fails with wrong balance, the bug is in bank.py deposit().
    3. Pick the file from the "Source files available" list above.
    4. Identify the exact line in the SOURCE file that contains the bug.
    5. Categorize the bug type: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION.

    MAPPING EXAMPLES:
    - test_bank.py fails → fix bank.py
    - test_calc.py fails → fix calc.py
    - test_validator.py fails → fix validator.py
    - ImportError for a module → fix the module file
    - SyntaxError → fix the file where the syntax error occurred (usually shown in traceback)

    Output strictly as JSON:
    {{
        "file": "source_file.py",
        "line": 10,
        "bug_type": "SYNTAX",
        "description": "Brief description of the actual bug in the source file"
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
