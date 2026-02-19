import os
from google import genai
from backend.nodes import env_loader  # noqa: F401 — loads backend/.env
from backend.state import AgentState, FixDetail

def fixer_node(state: AgentState) -> AgentState:
    """
    Generates code fixes and applies them to the repository.
    """
    print("Fixer Node Started...")
    
    analysis = state.get('current_analysis')
    if not analysis:
        print("No analysis found. Skipping fix.")
        return state

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
         print("CRITICAL: GOOGLE_API_KEY not found. Cannot generate fixes.")
         return state
        
    repo_path = state['repo_path']
    file_relative_path = analysis.get('file', '')

    if not file_relative_path:
        print("No file identified in analysis.")
        return state

    # Strip Docker container prefix (/app/ is the mount point)
    for prefix in ['/app/', '/app', 'app/']:
        if file_relative_path.startswith(prefix):
            file_relative_path = file_relative_path[len(prefix):]
            break

    # Also strip any leading slashes
    file_relative_path = file_relative_path.lstrip('/')

    file_full_path = os.path.join(repo_path, file_relative_path)

    if not os.path.exists(file_full_path):
        # Fallback: search for the file by basename within repo
        import glob as _glob
        basename = os.path.basename(file_relative_path)
        matches = _glob.glob(os.path.join(repo_path, '**', basename), recursive=True)
        matches = [m for m in matches if '__pycache__' not in m and '.git' not in m]
        if matches:
            file_full_path = matches[0]
            file_relative_path = os.path.relpath(file_full_path, repo_path).replace('\\', '/')
            print(f"Fixer: Resolved file via basename search: {file_relative_path}")
        else:
            print(f"Fixer: File not found (tried path + basename search): {file_relative_path}")
            return state

    with open(file_full_path, "r", encoding="utf-8") as f:
        code_content = f.read()
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert Autonomous AI Fixer.
    
    Context:
    File: {file_relative_path}
    Bug Type: {analysis.get('bug_type')}
    Line: {analysis.get('line')}
    Error Description: {analysis.get('description')}
    
    Original Code:
    ```python
    {code_content}
    ```
    
    Task:
    Fix the bug in the code. 
    1. Return the FULL updated file content.
    2. Ensure the fix addresses the specific error described.
    3. Do not add markdown backticks or explanations, just the raw code.
    
    Output Format:
    Only the raw code.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        fixed_code = response.text
        print(f"DEBUG: AI Generated Code:\n{fixed_code}\n-------------------")
        
        # Clean up markdown if Gemini adds it despite instructions
        if fixed_code.startswith("```"):
            lines = fixed_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            fixed_code = "\n".join(lines)
            
        # Apply Fix
        with open(file_full_path, "w", encoding="utf-8") as f:
            f.write(fixed_code)
            
        # Log Fix
        fix_entry: FixDetail = {
            "path": file_relative_path,
            "bug_type": analysis.get('bug_type'),
            "line": analysis.get('line'),
            "description": f"Fixed {analysis.get('bug_type')} error at line {analysis.get('line')}",
            "commit_message": f"[AI-AGENT] Fixed {analysis.get('bug_type')} in {file_relative_path}"
        }
        
        if 'fixes_applied' not in state:
            state['fixes_applied'] = []
            
        state['fixes_applied'].append(fix_entry)
        state['current_step'] = "FIX_APPLIED"
        print(f"Fix applied to {file_relative_path}")
        
    except Exception as e:
        print(f"Fixer Failed: {e}")
        
    return state
