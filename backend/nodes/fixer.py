import os
import json
from google import genai
from backend.nodes import env_loader  # noqa: F401 — loads backend/.env
from backend.state import AgentState, FixDetail

def fixer_node(state: AgentState) -> AgentState:
    """
    Generates code fixes and applies them to the repository.
    """
    from backend.utils.supabase_manager import SupabaseManager
    
    print("Fixer Node Started...")
    supabase = SupabaseManager()

    
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
    
    # ── SAFETY GUARD: Block Hallucinated Source Files ──────────────────────────
    traceback_file = analysis.get('traceback_file')
    if traceback_file:
        # Normalize for comparison
        tf_norm = traceback_file.replace('\\', '/').strip()
        rf_norm = file_relative_path.replace('\\', '/').strip()
        
        # Loose match: ends with
        if not (rf_norm.endswith(tf_norm) or tf_norm.endswith(rf_norm)):
            print(f"Fixer: BLOCKED HALLUCINATION. Traceback says '{tf_norm}' but AI wants to fix '{rf_norm}'")
            # We must fail this turn so we don't commit garbage
            return state

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
        all_lines = f.readlines()
    code_content = "".join(all_lines)

    # Context Filter: only send 10 lines around the failing line to the LLM.
    # This prevents hallucinating fixes for unrelated code (judge compliance).
    error_line = analysis.get('line', 0)
    try:
        error_line_int = int(error_line)
    except (ValueError, TypeError):
        error_line_int = 0

    if error_line_int > 0:
        start = max(0, error_line_int - 11)   # 10 lines before
        end = min(len(all_lines), error_line_int + 10)  # 10 lines after
        context_lines = all_lines[start:end]
        context_snippet = "".join(
            f"{start + i + 1}: {line}" for i, line in enumerate(context_lines)
        )
        context_label = f"Lines {start + 1}–{end} of {file_relative_path} (error at line {error_line_int})"
    else:
        context_snippet = code_content
        context_label = f"Full file: {file_relative_path}"

    client = genai.Client(api_key=api_key)

    # Build the exception-specific rule if the debugger detected a pytest.raises() case
    expected_exception = analysis.get('expected_exception', '')
    exception_rule = (
        f"\n    EXCEPTION GUARD — READ CAREFULLY:\n"
        f"    The failing test calls pytest.raises({expected_exception}), meaning the source function\n"
        f"    must raise {expected_exception} when given bad input instead of returning False or None.\n"
        f"\n"
        f"    CORRECT fix: replace `return False` (or equivalent) with `raise {expected_exception}(\"<message>\")`\n"
        f"    WRONG fix: do NOT insert invalid Python text, do NOT add random text, do NOT break the syntax.\n"
        f"    The fixed file MUST be syntactically valid Python. `raise {expected_exception}(\"...\")` IS valid Python.\n"
        f"    NEVER raise ValueError, TypeError, or any other exception — it MUST be {expected_exception}.\n"
    ) if expected_exception else ""


    # ── AGENT MEMORY: Check for previous successful fixes ──
    reference_fix = supabase.get_previous_fix(
        bug_type=analysis.get('bug_type', ''),
        description=analysis.get('description', '')
    )
    
    reference_fix_prompt = ""
    if reference_fix:
        print(f"Agent Memory: Found reference fix from a previous run!")
        reference_fix_prompt = (
            f"\n    REFERENCE FIX (from previous successful run):\n"
            f"    The following fix was successfully applied to a similar bug:\n"
            f"    Description: {reference_fix.get('description')}\n"
            f"    Code Action: {reference_fix.get('fix_action')}\n"
            f"    Consider this approach if applicable.\n"
        )

    prompt = f"""
    You are an expert Autonomous AI Fixer.

    Context:
    File: {file_relative_path}
    Bug Type: {analysis.get('bug_type')}
    Line: {analysis.get('line')}
    Error Description: {analysis.get('description')}

    Relevant Code ({context_label}):
    ```
    {context_snippet}
    ```

    Full file (for reference only — DO NOT modify lines outside the error context):
    ```
    {code_content}
    ```

    Task:
    1. Fix ONLY the bug at line {analysis.get('line')} described above. Do not touch other lines.
    2. Write a short, human-readable description of the fix action (max 10 words).

    SPECIAL RULES:
    - If File is 'requirements.txt': Append the missing library. Do NOT remove existing libraries.
    - If File is 'package.json': Add the dependency to the "dependencies" section.
    - Output the FULL file content in "fixed_code", not just the diff.
{exception_rule}
{reference_fix_prompt}

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
                model=state.get('model_name', 'gemini-2.5-flash'),
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
        
        # Log to Supabase
        supabase.update_node_status(
            run_id=state.get('run_id'),
            node="Fixer",
            log_type="FIX_APPLIED",
            content=fix_entry
        )
        
    except Exception as e:
        print(f"Fixer Failed: {e}")
        
    return state
