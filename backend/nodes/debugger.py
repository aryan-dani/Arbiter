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
    
    prompt = f"""
    You are an expert Python/Node.js debugger. 
    Analyze the following error logs from a CI/CD pipeline.
    
    Logs:
    {error_logs}
    
    Task:
    1. Identify the file path responsible for the error.
    2. If the error is an AssertionError in a test file, try to identify the source code file being tested (e.g., if test_calc.py fails, suspect calc.py).
    3. Identify the line number (if available).
    4. Categorize the bug into one of: LINTING, SYNTAX, LOGIC, TYPE_ERROR, IMPORT, INDENTATION.
    5. Provide a brief description of the error.
    
    Output strictly in JSON format:
    {{
        "file": "path/to/file",
        "line": 10,
        "bug_type": "SYNTAX",
        "description": "Missing colon at end of function definition"
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
