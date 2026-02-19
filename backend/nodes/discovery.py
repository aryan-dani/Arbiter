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
    if os.path.exists(repo_dir):
        # First attempt: pure Python (works on Windows and standard Linux)
        shutil.rmtree(repo_dir, ignore_errors=True)

        # Second attempt: if the directory still exists (root-owned files in Docker),
        # fall back to a subprocess rm -rf which runs with the parent process privileges.
        if os.path.exists(repo_dir):
            try:
                import subprocess
                subprocess.run(["rm", "-rf", repo_dir], check=False)
                print(f"Discovery: subprocess rm -rf cleaned {repo_dir}")
            except Exception as rm_err:
                print(f"Discovery: WARNING - Could not remove {repo_dir}: {rm_err}")

    os.makedirs(WORK_DIR, exist_ok=True)

    try:
        print(f"  Cloning {repo_url} -> {repo_dir}")
        Repo.clone_from(repo_url, repo_dir)
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
