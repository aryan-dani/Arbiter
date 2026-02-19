from git import Repo, Actor
import os
from datetime import datetime
from backend.state import AgentState


def _make_branch_name(team_name: str, leader_name: str) -> str:
    import re
    def sanitize(s):
        return re.sub(r"[^A-Z0-9_]", "", s.upper().replace(" ", "_").replace("-", "_"))
    
    return f"{sanitize(team_name)}_{sanitize(leader_name)}_AI_Fix"


def git_node(state: AgentState) -> AgentState:
    """
    Commits and pushes the applied fixes to the AI_Fix branch.
    """
    print("Git Node Started...")

    repo_path = state['repo_path']
    team_name = state['team_name']
    leader_name = state['leader_name']
    fixes = state.get('fixes_applied', [])

    if not fixes:
        print("No fixes to commit.")
        return state

    # Get the last fix's commit message
    last_fix = fixes[-1]
    commit_msg = last_fix.get('commit_message', '[AI-AGENT] Fix applied')

    # Ensure [AI-AGENT] prefix
    if not commit_msg.startswith('[AI-AGENT]'):
        commit_msg = f'[AI-AGENT] {commit_msg}'

    try:
        repo = Repo(repo_path)
    except Exception as e:
        print(f"Git: Could not open repo at {repo_path}: {e}")
        return state

    author = Actor("AI Agent", "agent@rift2026.com")
    committer = Actor("AI Agent", "agent@rift2026.com")

    branch_name = _make_branch_name(team_name, leader_name)
    print(f"Git: Target branch = {branch_name}")

    # Create or checkout branch
    try:
        if branch_name not in [h.name for h in repo.heads]:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            print(f"Git: Created new branch '{branch_name}'")
        else:
            repo.heads[branch_name].checkout()
            print(f"Git: Checked out existing branch '{branch_name}'")
    except Exception as e:
        print(f"Git: Branch checkout failed: {e}")
        return state

    try:
        # ── Atomic Cleanup: Replaces git clean -fd with permission-safe purge ──
        import subprocess
        subprocess.run('find . -name "__pycache__" -type d -exec rm -rf {} +', shell=True, check=False, cwd=repo_path)
        subprocess.run('find . -name "*.pyc" -delete', shell=True, check=False, cwd=repo_path)

        repo.git.execute(["git", "rm", "-r", "--cached", ".", "--ignore-unmatch"])
        gitignore_path = os.path.join(repo_path, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("__pycache__/\n*.pyc\n.pytest_cache/\n.env\n")
        repo.git.add(".gitignore")
        repo.git.add(all=True)

        # Check if there are actually changes to commit
        if repo.is_dirty(untracked_files=True) or repo.index.diff("HEAD"):
            repo.index.commit(commit_msg, author=author, committer=committer)
            print(f"Git: Committed — '{commit_msg}'")
        else:
            print("Git: No changes to commit (skipping).")
    except Exception as e:
        print(f"Git: Commit failed: {e}")
        return state

    # ── Force-Rebase Push ────────────────────────────────────────────────────
    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        clean_remote_url = repo.remotes.origin.url

        if github_token:
            raw_url = clean_remote_url
            if "@github.com" in raw_url:
                raw_url = "https://github.com" + raw_url.split("@github.com", 1)[1]
                clean_remote_url = raw_url

            if raw_url.startswith("https://"):
                authed_url = raw_url.replace("https://", f"https://{github_token}@")
                repo.remotes.origin.set_url(authed_url)

        # Implementation of "git pull --rebase origin {branch_name} && git push origin {branch_name}"
        # This handles the "failed to push some refs" error gracefully.
        print(f"Git: Pulling with rebase from origin {branch_name}...")
        try:
            repo.git.pull('origin', branch_name, rebase=True)
        except Exception as pull_err:
            print(f"Git: Pull --rebase failed (might be first push): {pull_err}")

        repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}")
        print(f"Git: Pushed branch '{branch_name}' to origin.")
        state['branch_pushed'] = True

        # ── Open a Pull Request only on the first push ───────────────
        if not state.get('pr_url') and github_token:
            try:
                import urllib.request
                import json as _json

                # Parse owner/repo from clean remote URL (no token)
                clean_url = clean_remote_url.replace("https://", "").replace(".git", "")
                parts = clean_url.strip("/").split("/")  # ['github.com', 'owner', 'repo']
                if len(parts) >= 3:
                    owner, repo_name = parts[-2], parts[-1]

                    # CHECK FOR EXISTING PR FIRST to avoid 422
                    # There isn't an easy way to check without listing all PRs, which might be overkill.
                    # Instead, we will handle the 422 specific error in the exception block below.

                    pr_body = {
                        "title": f"[AI-AGENT] Autonomous CI/CD Fix — {branch_name}",
                        "body": (
                            "## AI-Agent Auto-Fix\n\n"
                            "This pull request was created automatically by the **RIFT 2026 CI/CD Healing Agent**.\n\n"
                            f"**Branch:** `{branch_name}`\n"
                            f"**Fixes Applied:** {len(state.get('fixes_applied', []))}\n\n"
                            "All changes were committed with the `[AI-AGENT]` prefix."
                        ),
                        "head": branch_name,
                        "base": "main",
                    }

                    pr_data = _json.dumps(pr_body).encode("utf-8")
                    pr_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                    req = urllib.request.Request(
                        pr_api_url,
                        data=pr_data,
                        headers={
                            "Authorization": f"token {github_token}",
                            "Accept": "application/vnd.github.v3+json",
                            "Content-Type": "application/json",
                            "User-Agent": "RIFT2026-Agent",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req) as resp:
                        pr_result = _json.loads(resp.read().decode())
                        pr_html_url = pr_result.get("html_url", "")
                        print(f"Git: PR created → {pr_html_url}")
                        state['pr_url'] = pr_html_url
            except urllib.error.HTTPError as http_err:
                if http_err.code == 422:
                     print(f"Git: PR creation skipped (422 Unprocessable Entity) - likely already exists.")
                     # Ideally we'd fetch the existing PR URL here but for now just suppressing the error is enough
                else:
                     print(f"Git: PR creation failed: {http_err}")
            except Exception as pr_err:
                print(f"Git: PR creation failed: {pr_err}")
        elif state.get('pr_url'):
            print(f"Git: PR already open at {state['pr_url']} — skipping duplicate creation.")


    except Exception as e:
        print(f"Git: Push failed (will continue without push): {e}")
        state['branch_pushed'] = False

    state['branch_name'] = branch_name
    state['current_step'] = "GIT_COMMIT_COMPLETE"
    return state
