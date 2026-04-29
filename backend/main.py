from contextlib import asynccontextmanager
import os
import json
import sys
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Ensure we can import from backend package even if running from inside backend folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_backend_dir, ".env")
_env_local_path = os.path.join(_backend_dir, ".env.local")
load_dotenv(dotenv_path=_env_path, override=True)
load_dotenv(dotenv_path=_env_local_path, override=True)


def _parse_cors_origins() -> list:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "https://thearbiter.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.utils.db_manager import DbManager

    DbManager().init_schema()
    yield


from backend.graph import create_workflow, get_workflow_config
from backend.state import AgentState

app = FastAPI(
    title="Arbiter — Autonomous CI/CD Healing API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "results.json",
)

run_status: dict = {}


class HealingRequest(BaseModel):
    repo_url: str
    team_name: str
    leader_name: str
    max_iterations: int = 10
    model_name: str = "gemini-2.5-flash"


def _sanitize(s: str) -> str:
    import re

    return re.sub(r"[^A-Z0-9_]", "", s.upper().replace(" ", "_"))


def _branch_name(team: str, leader: str) -> str:
    return f"{_sanitize(team)}_{_sanitize(leader)}_AI_Fix"


async def run_healing_workflow(request: HealingRequest, run_id: str = None):
    from backend.utils.db_manager import DbManager

    key = request.team_name
    run_status[key] = {"status": "running", "team_name": request.team_name}

    start_time = datetime.now()

    db = DbManager()
    if run_id:
        print(f"Workflow started with Run ID: {run_id}")
    else:
        print("WARNING: No run_id provided to workflow. Logging disabled.")

    workflow_app = create_workflow()

    initial_state = AgentState(
        today=datetime.now().strftime("%Y-%m-%d"),
        repo_url=request.repo_url,
        team_name=request.team_name,
        leader_name=request.leader_name,
        repo_path="",
        upstream_url=request.repo_url,
        fork_url="",
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
        max_iterations=request.max_iterations,
        iterations=0,
        run_id=run_id,
        model_name=request.model_name,
    )

    try:
        final_state = await workflow_app.ainvoke(
            initial_state, config=get_workflow_config()
        )

        duration = final_state.get("total_time", 0.0)
        fixes = final_state.get("fixes_applied", [])

        final_score = final_state.get("final_score", 0)
        breakdown = final_state.get("current_analysis", {}).get(
            "scoring_breakdown", {}
        )
        base_score = breakdown.get("base_score", 0)
        speed_bonus = breakdown.get("speed_bonus", 0)
        efficiency_penalty = breakdown.get("efficiency_penalty", 0)

        result_entry = {
            "repo_url": final_state["repo_url"],
            "team_name": final_state["team_name"],
            "leader_name": final_state["leader_name"],
            "branch_name": _branch_name(final_state["team_name"], final_state["leader_name"]),
            "final_status": final_state.get("final_status", "UNKNOWN"),
            "total_time": duration,
            "final_score": final_score,
            "base_score": base_score,
            "speed_bonus": speed_bonus,
            "efficiency_penalty": efficiency_penalty,
            "fixes_applied": fixes,
            "timeline": final_state.get("timeline", []),
            "retry_count": final_state.get("retry_count", 0),
            "completed_at": datetime.now().isoformat(),
            "started_at": start_time.isoformat(),
        }

        status_map = {
            "PASSED": "SUCCESS",
            "FAILED": "FAILED",
            "ERROR": "FAILED",
            "DISCOVERY_FAILED": "FAILED",
            "NO_BUGS_FOUND": "SUCCESS",
        }
        db_status = status_map.get(final_state.get("final_status"), "FAILED")

        db.finalize_run(
            run_id=run_id,
            score=final_score,
            duration=duration,
            status=db_status,
            pr_url=final_state.get("pr_url"),
            branch_name=final_state.get("branch_name")
            or _branch_name(final_state["team_name"], final_state["leader_name"]),
        )

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


@app.post("/start-healing")
async def start_healing(request: HealingRequest, background_tasks: BackgroundTasks):
    from backend.utils.db_manager import DbManager

    db = DbManager()
    run_id = db.create_run(
        run_name=f"{request.team_name}-{request.leader_name}",
        target_repo=request.repo_url,
        team_name=request.team_name,
        leader_name=request.leader_name,
    )

    background_tasks.add_task(run_healing_workflow, request, run_id)

    return {
        "message": "Healing process started in background",
        "repo_url": request.repo_url,
        "team_name": request.team_name,
        "branch_name": _branch_name(request.team_name, request.leader_name),
        "status": "running",
        "run_id": run_id,
    }


@app.get("/status/{team_name}")
async def get_status(team_name: str):
    entry = run_status.get(team_name)
    if not entry:
        existing = _load_results()
        for r in reversed(existing):
            if r.get("team_name") == team_name:
                return {"status": "done", "result": r}
        return {"status": "not_found"}
    return entry


@app.get("/results")
async def get_results():
    try:
        return _load_results()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/stats/summary")
async def api_stats_summary():
    from backend.utils.db_manager import DbManager

    db = DbManager()
    return {
        "total_runs": db.count_runs(),
        "last_run_status": db.last_run_status(),
    }


@app.get("/api/runs")
async def api_runs():
    from backend.utils.db_manager import DbManager

    return DbManager().list_runs()


@app.get("/api/runs/{run_id}")
async def api_run_detail(run_id: str):
    from backend.utils.db_manager import DbManager

    row = DbManager().get_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


@app.get("/api/runs/{run_id}/logs")
async def api_run_logs(run_id: str):
    from backend.utils.db_manager import DbManager

    return {"logs": DbManager().list_logs_for_run(run_id)}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    # Only watch `backend/` so clones under `temp_repos/` do not trigger mid-run reload.
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(root / "backend")],
    )
