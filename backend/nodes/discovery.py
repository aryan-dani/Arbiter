import os
import shutil
import glob
import stat
from git import Repo
from backend.state import AgentState

# Use absolute path for temp_repos relative to project root (3 levels up from nodes/discovery.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK_DIR = os.path.join(BASE_DIR, "temp_repos")


def _remove_readonly(func, path, _):
    """Force-delete read-only files on Windows (needed for .git dirs)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def discovery_node(state: AgentState) -> AgentState:
    """
    Clones the repository, detects the stack, and finds test files.
    """
    print("Discovery Node Started...")
    repo_url = state['repo_url']
    team_name = state['team_name']

    # Create a unique path for the repo
    repo_dir = os.path.join(
        WORK_DIR,
        f"{team_name}_{os.path.basename(repo_url.rstrip('/')).replace('.git', '')}"
    )

    # ── Ironclad Cleanup: handles Docker root-owned __pycache__ files ──────────
    # We want to ensure the directory is absolutely gone before cloning.
    if os.path.exists(repo_dir):
        print(f"Discovery: Cleaning up existing directory {repo_dir}...")
        
        # Method 1: Standard Python shutil
        try:
            shutil.rmtree(repo_dir, onerror=_remove_readonly)
        except Exception as e:
            print(f"Discovery: shutil.rmtree failed ({e}), trying subprocess...")

        # Method 2: Platform-specific subprocess (Force kill)
        if os.path.exists(repo_dir):
            try:
                import subprocess
                if os.name == 'nt':
                    # Windows: use rmdir /s /q
                    subprocess.run(["rmdir", "/s", "/q", repo_dir], shell=True, check=False)
                else:
                    # Linux/Docker: use rm -rf (handles root-owned files better)
                    subprocess.run(["rm", "-rf", repo_dir], check=False)
                
                print(f"Discovery: subprocess cleanup attempted.")
            except Exception as rm_err:
                print(f"Discovery: WARNING - Subprocess cleanup failed: {rm_err}")
    
    # Verify cleanup
    if os.path.exists(repo_dir):
        print(f"CRITICAL: Failed to clean {repo_dir}. Cloning might fail or use stale files.")
    else:
        print(f"Discovery: Cleanup successful.")

    os.makedirs(WORK_DIR, exist_ok=True)

    # ── Forking Logic ────────────────────────────────────────────────────────
    # If we have a GITHUB_TOKEN, we try to fork the repo to the user's account
    # and clone from there. If not, we clone directly (read-only or public).
    
    github_token = os.environ.get("GITHUB_TOKEN")
    upstream_url = state['repo_url']
    fork_url = ""
    
    if github_token:
        print(f"Discovery: Found GITHUB_TOKEN. Attempting to ensure fork exists...")
        try:
            fork_url = _ensure_fork(upstream_url, github_token)
            if fork_url:
                print(f"Discovery: Fork ready at {fork_url}")
                state['fork_url'] = fork_url
                state['upstream_url'] = upstream_url
                # Clone from the FORK, not the upstream
                clone_url = fork_url.replace("https://", f"https://{github_token}@")
            else:
                print("Discovery: Fork creation returned empty URL. Falling back to direct clone.")
                clone_url = upstream_url
        except Exception as e:
            print(f"Discovery: Forking failed ({e}). Falling back to direct clone.")
            clone_url = upstream_url
    else:
        print("Discovery: No GITHUB_TOKEN found. Cloning upstream directly (read-only?).")
        clone_url = upstream_url

    try:
        # If we have a token but forking failed/skipped, inject token into upstream URL if needed?
        # Only if we plan to push to upstream directly (which we shouldn't if we don't own it).
        # For now, let's assume if no fork, we clone read-only or however the URL is provided.
        
        print(f"  Cloning {clone_url} -> {repo_dir}")
        Repo.clone_from(clone_url, repo_dir)
    except Exception as e:
        print(f"CRITICAL: Clone failed: {e}")
        state['repo_path'] = repo_dir
        state['detected_stack'] = "UNKNOWN"
        state['test_files'] = []
        state['current_step'] = "DISCOVERY_FAILED"
        return state

    # ── Clone sanity check: prevent False-Green on zombie directory ───────────
    cloned_files = os.listdir(repo_dir) if os.path.exists(repo_dir) else []
    if not cloned_files:
        print("CRITICAL: Clone directory is empty — treating as clone failure.")
        state['repo_path'] = repo_dir
        state['detected_stack'] = "UNKNOWN"
        state['test_files'] = []
        state['current_step'] = "DISCOVERY_FAILED"
        return state

    # ── Stack Detection (order matters — check most specific first) ──
    detected_stack = "UNKNOWN"
    has_requirements = _find_file(repo_dir, "requirements.txt")
    has_pyproject = _find_file(repo_dir, "pyproject.toml")
    has_setup_py = _find_file(repo_dir, "setup.py")
    has_py_files = bool(glob.glob(os.path.join(repo_dir, "**", "*.py"), recursive=True))
    has_package_json = _find_file(repo_dir, "package.json")

    if has_requirements or has_pyproject or has_setup_py or has_py_files:
        detected_stack = "PYTHON"
    elif has_package_json:
        detected_stack = "NODE"

    # ── Find Test Files ──
    test_files = []
    if detected_stack == "PYTHON":
        patterns = [
            os.path.join(repo_dir, "**", "test_*.py"),
            os.path.join(repo_dir, "**", "*_test.py"),
        ]
        for pattern in patterns:
            test_files.extend(glob.glob(pattern, recursive=True))
    elif detected_stack == "NODE":
        patterns = [
            os.path.join(repo_dir, "**", "*.test.js"),
            os.path.join(repo_dir, "**", "*.spec.js"),
            os.path.join(repo_dir, "**", "*.test.ts"),
            os.path.join(repo_dir, "**", "*.spec.ts"),
        ]
        for pattern in patterns:
            test_files.extend(glob.glob(pattern, recursive=True))

    # Deduplicate and exclude node_modules/__pycache__
    test_files = list(set([
        f for f in test_files
        if "node_modules" not in f and "__pycache__" not in f
    ]))

    # ── Zero-test guard: a 0-test result means the scan failed or the
    # zombie directory tricked the agent. Flag it so the pipeline short-circuits.
    if len(test_files) == 0 and detected_stack == "PYTHON":
        print("CRITICAL: No test files found for a PYTHON repo — flagging DISCOVERY_FAILED.")
        state['repo_path'] = repo_dir
        state['detected_stack'] = detected_stack
        state['test_files'] = []
        state['current_step'] = "DISCOVERY_FAILED"
        return state

    # Update State
    state['repo_path'] = repo_dir
    state['detected_stack'] = detected_stack
    state['test_files'] = test_files
    state['current_step'] = "DISCOVERY_COMPLETE"

    print(f"Discovery Complete: Stack={detected_stack}, Found {len(test_files)} tests.")
    if test_files:
        for tf in test_files[:10]:
            print(f"  - {os.path.relpath(tf, repo_dir)}")

    return state


def _find_file(base_dir: str, filename: str) -> bool:
    """Search recursively for a file (up to 3 levels deep)."""
    for root, _, files in os.walk(base_dir):
        # Limit depth to avoid digging into node_modules etc.
        depth = root.replace(base_dir, '').count(os.sep)
        if depth > 3:
            continue
        if "node_modules" in root or ".git" in root:
            continue
        if filename in files:
            return True
    return False


def _ensure_fork(upstream_url: str, token: str) -> str | None:
    """
    Ensures a fork of the upstream repo exists on the authenticated user's account.
    Returns the URL of the fork (e.g. https://github.com/my-user/repo.git).
    """
    import requests
    import time

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Parse upstream owner/repo
    # Expected format: https://github.com/owner/repo or https://github.com/owner/repo.git
    clean = upstream_url.replace(".git", "").replace("https://github.com/", "").strip("/")
    parts = clean.split("/")
    if len(parts) < 2:
        print(f"Discovery: Could not parse owner/repo from {upstream_url}")
        return None
    
    upstream_owner, repo_name = parts[-2], parts[-1]

    # 2. Get authenticated user
    resp = requests.get("https://api.github.com/user", headers=headers)
    if resp.status_code != 200:
        print(f"Discovery: Failed to get auth user: {resp.text}")
        return None
    user_login = resp.json()["login"]

    # 3. Check if fork already exists
    fork_url = f"https://github.com/{user_login}/{repo_name}.git"
    
    # Check if we can access the fork (it might already exist)
    # We verify by checking API for this repo
    check_url = f"https://api.github.com/repos/{user_login}/{repo_name}"
    resp = requests.get(check_url, headers=headers)
    
    if resp.status_code == 200:
        print(f"Discovery: Fork already exists at {fork_url}")
        return fork_url

    # 4. Create Fork
    print(f"Discovery: Creating fork of {upstream_owner}/{repo_name}...")
    create_fork_url = f"https://api.github.com/repos/{upstream_owner}/{repo_name}/forks"
    resp = requests.post(create_fork_url, headers=headers)
    
    if resp.status_code not in [200, 202]:
        print(f"Discovery: Failed to create fork: {resp.text}")
        return None
    
    # 5. Wait for fork to be ready
    # GitHub returns 202 Accepted, but the repo might not be available immediately for cloning
    print("Discovery: Fork initiated. Waiting for readiness...")
    for i in range(10):
        time.sleep(2)
        resp = requests.get(check_url, headers=headers)
        if resp.status_code == 200:
            print(f"Discovery: Fork ready after {i*2}s.")
            return fork_url
    
    print("Discovery: Timed out waiting for fork to be ready.")
    return None
