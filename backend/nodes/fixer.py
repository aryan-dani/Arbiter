import os
import json
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
    ```
    {code_content}
    ```
    
    Task:
    1. Fix the bug described above.
    2. Write a short, human-readable description of the fix action (max 10 words).
    
    SPECIAL RULES:
    - If File is 'requirements.txt': Append the missing library. Do NOT remove existing libraries.
    - If File is 'package.json': Add the dependency to the "dependencies" section.
    - Output the FULL file content in "fixed_code", not just the diff.
    
    Output strictly as JSON (no markdown):
    {{
        "fixed_code": "<the full fixed file content as a string>",
        "fix_action": "<short fix description, e.g. 'remove the import statement' or 'add the colon at the correct position'>"
    }}
    """

    import time
    
    # Retry logic for 429 RESOURCE_EXHAUSTED
    max_retries = 5
    retry_delay = 10  # Start with 10 seconds as requested
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            break # Success
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt < max_retries:
                    print(f"Fixer: 429 RESOURCE_EXHAUSTED. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print("Fixer: Max retries exceeded for API limit.")
                    return state
            else:
                # Not a rate limit error, raise or handle
                print(f"Fixer: API Error: {e}")
                return state
        
    try:
        raw_text = response.text
        # robust cleanup of markdown fences
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_text = "\n".join(lines).strip()

        try:
            result = json.loads(cleaned_text)
            fixed_code = result.get('fixed_code', '')
            fix_action = result.get('fix_action', f'fix the {analysis.get("bug_type", "error").lower()} error')
            
            # If fixed_code is empty, stick with empty string or handle error
            if not fixed_code.strip():
                 # fallback if JSON is valid but code is empty - likely an error in generation
                 print("Fixer: Generated JSON has empty fixed_code.")
        except json.JSONDecodeError:
            # If it fails to parse as JSON, check if it looks like code or JSON
            # heuristic: if it starts with '{' and ends with '}', it's probably broken JSON. 
            # If it's code, it likely won't.
            if cleaned_text.strip().startswith("{") and cleaned_text.strip().endswith("}"):
                print("Fixer: Failed to parse JSON response. Raw response was likely malformed JSON.")
                # We could try to salvage, but for now let's just log and maybe return state
                # to avoid writing garbage.
                print(f"DEBUG Raw: {cleaned_text[:100]}...")
                return state
            else:
                # Assume it's raw code if it doesn't look like JSON
                print("Fixer: JSON parse failed, assuming raw code response.")
                fixed_code = cleaned_text
                fix_action = f'fix the {analysis.get("bug_type", "error").lower()} error'

            
        # Apply Fix
        with open(file_full_path, "w", encoding="utf-8") as f:
            f.write(fixed_code)
            
        # Judge-compliant output format:
        # 'LINTING error in src/utils.py line 15 → Fix: remove the import statement'
        bug_type = analysis.get('bug_type', 'UNKNOWN')
        line_num = analysis.get('line', '?')
        judge_description = f"{bug_type} error in {file_relative_path} line {line_num} \u2192 Fix: {fix_action}"
        print(f"[JUDGE OUTPUT] {judge_description}")

        fix_entry: FixDetail = {
            "path": file_relative_path,
            "bug_type": bug_type,
            "line": line_num,
            "description": judge_description,
            "commit_message": f"[AI-AGENT] {bug_type} fix in {file_relative_path} line {line_num}: {fix_action}"
        }
        
        if 'fixes_applied' not in state:
            state['fixes_applied'] = []
            
        state['fixes_applied'].append(fix_entry)
        state['current_step'] = "FIX_APPLIED"
        print(f"Fix applied to {file_relative_path}")
        
    except Exception as e:
        print(f"Fixer Failed: {e}")
        
    return state
