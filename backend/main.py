from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from datetime import datetime
import os
import json
import sys
from dotenv import load_dotenv

# Ensure we can import from backend package even if running from inside backend folder
# This adds the parent directory of 'backend' (i.e., the project root) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load environment variables — always use backend/.env regardless of CWD
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=True)

from backend.graph import create_workflow, get_workflow_config
from backend.state import AgentState

app = FastAPI(title="RIFT 2026 CI/CD Healing Backend")

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://thearbiter.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use absolute path for results.json so it's always in the project root
RESULTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results.json")

# ── In-memory run status tracker ──────────────────────────────────
run_status: dict = {}   # keyed by team_name for simplicity

# ── Request Model ─────────────────────────────────────────────────
class HealingRequest(BaseModel):
    repo_url: str
    team_name: str
    leader_name: str
    max_iterations: int = 5
    model_name: str = "gemini-2.5-flash"


def _sanitize(s: str) -> str:
    import re
    return re.sub(r"[^A-Z0-9_]", "", s.upper().replace(" ", "_"))


def _branch_name(team: str, leader: str) -> str:
    return f"{_sanitize(team)}_{_sanitize(leader)}_AI_Fix"


async def run_healing_workflow(request: HealingRequest, run_id: str = None):
    """
    Executes the LangGraph workflow and saves results.
    """
    from backend.utils.supabase_manager import SupabaseManager
    
    key = request.team_name
    run_status[key] = {"status": "running", "team_name": request.team_name}

    start_time = datetime.now()
    
    # Initialize Supabase
    supabase = SupabaseManager()
    if run_id:
        print(f"Workflow started with Supabase Run ID: {run_id}")
    else:
        print("WARNING: No run_id provided to workflow. Logging disabled.")

    workflow_app = create_workflow()

    # Initialize State
    initial_state = AgentState(
        today=datetime.now().strftime("%Y-%m-%d"),
        repo_url=request.repo_url,
        team_name=request.team_name,
        leader_name=request.leader_name,
        repo_path="",
        upstream_url=request.repo_url,  # Initially same as repo_url, discovery will update if forking
        fork_url="",                    # Will be populated by discovery_node
        start_time=start_time.timestamp(),
        current_step="START",
        retry_count=0,
        error_logs="",
        detected_stack="UNKNOWN",
        test_files=[],
        fixes_applied=[],
        timeline=[],
        final_status="PENDING",
        total_time=0.0,
        final_score=0,
        is_healing_complete=False,
        current_analysis={},

        # Rate Limiting (Default: 5 loops max to prevent infinite API usage)
        max_iterations=request.max_iterations,
        iterations=0,
        run_id=run_id,
        model_name=request.model_name
    )

    try:
        final_state = await workflow_app.ainvoke(initial_state, config=get_workflow_config())

        duration = final_state.get('total_time', 0.0)
        fixes = final_state.get('fixes_applied', [])
        
        # Scoring is now handled inside the graph by scoring_node
        final_score = final_state.get('final_score', 0)
        breakdown = final_state.get('current_analysis', {}).get('scoring_breakdown', {})
        base_score = breakdown.get('base_score', 0)
        speed_bonus = breakdown.get('speed_bonus', 0)
        efficiency_penalty = breakdown.get('efficiency_penalty', 0)

        # Save Results
        result_entry = {
            "repo_url": final_state['repo_url'],
            "team_name": final_state['team_name'],
            "leader_name": final_state['leader_name'],
            "branch_name": _branch_name(final_state['team_name'], final_state['leader_name']),
            "final_status": final_state.get('final_status', 'UNKNOWN'),
            "total_time": duration,
            "final_score": final_score,
            "base_score": base_score,
            "speed_bonus": speed_bonus,
            "efficiency_penalty": efficiency_penalty,
            "fixes_applied": fixes,
            "timeline": final_state.get('timeline', []),
            "retry_count": final_state.get('retry_count', 0),
            "completed_at": datetime.now().isoformat(),
            "started_at": start_time.isoformat(),
        }

        # Update Supabase Final Status
        supabase.finalize_run(
            run_id=run_id,
            score=final_score,
            duration=duration,
            status=final_state.get('final_status', 'UNKNOWN'),
            pr_url=final_state.get('pr_url'),
            branch_name=_branch_name(final_state['team_name'], final_state['leader_name'])
        )

        # Load and append
        existing_results = _load_results()
        existing_results.append(result_entry)
        _save_results(existing_results)

        run_status[key] = {"status": "done", "result": result_entry}
        print(f"Healing run completed for {request.team_name}. Score: {final_state.get('final_score')}")

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"Workflow execution failed: {err}")
        run_status[key] = {"status": "error", "error": str(e)}


def _load_results():
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return []


def _save_results(data):
    with open(RESULTS_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ── Endpoints ─────────────────────────────────────────────────────

@app.post("/start-healing")
async def start_healing(request: HealingRequest, background_tasks: BackgroundTasks):
    """
    Triggers the autonomous healing process for the given repository.
    """
    from backend.utils.supabase_manager import SupabaseManager
    
    # Create Supabase Run Synchronously
    supabase = SupabaseManager()
    run_id = supabase.create_run(
        run_name=f"{request.team_name}-{request.leader_name}",
        target_repo=request.repo_url
    )
    
    background_tasks.add_task(run_healing_workflow, request, run_id)
    
    return {
        "message": "Healing process started in background",
        "repo_url": request.repo_url,
        "team_name": request.team_name,
        "branch_name": _branch_name(request.team_name, request.leader_name),
        "status": "running",
        "run_id": run_id
    }


@app.get("/status/{team_name}")
async def get_status(team_name: str):
    """
    Returns the status of a healing run for a given team.
    """
    entry = run_status.get(team_name)
    if not entry:
        # Fall back to checking results file for completed past runs
        existing = _load_results()
        for r in reversed(existing):
            if r.get("team_name") == team_name:
                return {"status": "done", "result": r}
        return {"status": "not_found"}
    return entry


@app.get("/results")
async def get_results():
    """
    Returns the history of all healing runs.
    """
    try:
        return _load_results()
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
