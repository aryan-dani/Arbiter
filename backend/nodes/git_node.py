from git import Repo, Actor
import os
from datetime import datetime
from backend.state import AgentState


def _make_branch_name(team_name: str, leader_name: str) -> str:
    team = team_name.upper().replace(" ", "_").replace("-", "_")
    leader = leader_name.upper().replace(" ", "_").replace("-", "_")
    return f"{team}_{leader}_AI_Fix"


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

    # Stage ALL modified/untracked changes
    try:
        repo.git.add(A=True)   # --all: stages new, modified, and deleted files
        if repo.is_dirty(untracked_files=True):
            repo.index.commit(commit_msg, author=author, committer=committer)
            print(f"Git: Committed — '{commit_msg}'")
        else:
            print("Git: No changes to commit.")
    except Exception as e:
        print(f"Git: Commit failed: {e}")
        return state

    # Push to remote (requires the remote repo to have been authenticated)
    # We use the origin URL as-is; GitHub token auth is via GITHUB_TOKEN in .env
    try:
        github_token = os.environ.get("GITHUB_TOKEN")
        clean_remote_url = repo.remotes.origin.url  # always the clean URL before auth injection

        if github_token:
            # Strip any previously injected token to avoid double-injection on retries
            raw_url = clean_remote_url
            if "@github.com" in raw_url:
                # Already has a token injected — strip it out first
                raw_url = "https://github.com" + raw_url.split("@github.com", 1)[1]
                clean_remote_url = raw_url

            if raw_url.startswith("https://"):
                authed_url = raw_url.replace("https://", f"https://{github_token}@")
                repo.remotes.origin.set_url(authed_url)

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
            except Exception as pr_err:
                print(f"Git: PR creation failed (branch was pushed OK): {pr_err}")
        elif state.get('pr_url'):
            print(f"Git: PR already open at {state['pr_url']} — skipping duplicate creation.")


    except Exception as e:
        print(f"Git: Push failed (will continue without push): {e}")
        state['branch_pushed'] = False

    state['branch_name'] = branch_name
    state['current_step'] = "GIT_COMMIT_COMPLETE"
    return state
