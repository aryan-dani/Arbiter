from git import Repo, Actor
import os
from datetime import datetime
from backend.state import AgentState


def _make_branch_name(team_name: str, leader_name: str) -> str:
    return (
        f"{team_name}_{leader_name}_AI_Fix"
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )


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
        if github_token:
            # Inject token into remote URL for HTTPS auth
            remote_url = repo.remotes.origin.url
            if remote_url.startswith("https://"):
                authed_url = remote_url.replace(
                    "https://",
                    f"https://{github_token}@"
                )
                repo.remotes.origin.set_url(authed_url)

        repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}")
        print(f"Git: Pushed branch '{branch_name}' to origin.")
        state['branch_pushed'] = True
    except Exception as e:
        print(f"Git: Push failed (will continue without push): {e}")
        state['branch_pushed'] = False

    state['branch_name'] = branch_name
    state['current_step'] = "GIT_COMMIT_COMPLETE"
    return state
