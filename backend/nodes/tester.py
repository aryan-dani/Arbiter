import os
import re
import subprocess
import sys
from datetime import datetime

import docker

from backend.state import AgentState
from backend.scoring import calculate_score


def _env_truthy(key: str, default: bool = True) -> bool:
    v = os.environ.get(key)
    if v is None or str(v).strip() == "":
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _get_docker_client():
    """Returns a live Docker client or None if the daemon is not reachable."""
    for label, factory in (
        ("DOCKER_HOST / default", lambda: docker.from_env()),
        ("Windows npipe", lambda: docker.DockerClient(base_url="npipe:////./pipe/docker_engine")),
        ("tcp 127.0.0.1:2375", lambda: docker.DockerClient(base_url="tcp://127.0.0.1:2375")),
    ):
        try:
            c = factory()
            c.ping()
            print(f"    Docker connected via {label}.")
            return c
        except Exception:
            continue
    print("    Docker daemon not reachable — start Docker Desktop (Windows/macOS) or the docker service (Linux).")
    return None


def _run_pytest_on_host(repo_path: str) -> tuple[str, int]:
    """Non-sandboxed fallback when Docker is unavailable (dev convenience)."""
    print("  [host-tests] Running: python -m pytest -v --tb=long (sandbox off; install target deps in repo venv for best results)")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=long"],
        cwd=repo_path,
        capture_output=True,
        timeout=300,
        text=False,
    )
    blob = (r.stdout or b"") + (r.stderr or b"")
    logs = blob.decode("utf-8", errors="replace")
    return logs, r.returncode


def _run_python_main_on_host(repo_path: str) -> tuple[str, int]:
    if not os.path.isfile(os.path.join(repo_path, "main.py")):
        return "(no main.py at repo root; skip host fallback)\n", 1
    r = subprocess.run(
        [sys.executable, "main.py"],
        cwd=repo_path,
        capture_output=True,
        timeout=120,
        text=False,
    )
    blob = (r.stdout or b"") + (r.stderr or b"")
    return blob.decode("utf-8", errors="replace"), r.returncode


def tester_node(state: AgentState) -> AgentState:
    """
    Runs tests in Docker when available; optionally falls back to host pytest when Docker is off.
    """
    print("Tester Node Started...")

    client = _get_docker_client()

    repo_path = state["repo_path"]
    stack = state["detected_stack"]

    container_logs = ""
    exit_code = 1

    abs_repo_path = os.path.abspath(repo_path)
    host_only = False
    command = ""
    image = "python:3.11-slim"

    if client is not None:
        if stack == "PYTHON":
            command = (
                "bash -c '"
                "export PYTHONDONTWRITEBYTECODE=1; "
                "export PYTHONPATH=$PYTHONPATH:$(pwd)/src:$(pwd); "
                "pip install flake8 pytest --quiet -q > /dev/null 2>&1; "
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet -q > /dev/null 2>&1); "
                "([ -d src ] && flake8 src/ --count --select=F401,E9,F63,F7,F82 --show-source --statistics || true); "
                "pytest -v --tb=long 2>&1"
                "'"
            )
            image = "python:3.11-slim"
        elif stack == "NODE":
            command = (
                "bash -c '"
                "export PYTHONDONTWRITEBYTECODE=1; "
                "npm install --silent 2>/dev/null && "
                "(npm test 2>&1 || true)'"
            )
            image = "node:18"
        else:
            command = (
                "bash -c '"
                "export PYTHONDONTWRITEBYTECODE=1; "
                "pip install pytest --quiet -q > /dev/null 2>&1; "
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet -q > /dev/null 2>&1); "
                "pytest -v --tb=long 2>&1'"
            )
            image = "python:3.11-slim"
    else:
        if stack == "PYTHON" and _env_truthy("ARBITER_ALLOW_HOST_TESTS", True):
            container_logs, exit_code = _run_pytest_on_host(abs_repo_path)
            host_only = True
        else:
            container_logs = (
                "Docker is not running.\n\n"
                "• Install and start Docker Desktop (Windows/macOS) or the linux docker service.\n"
                "• For Python repos only, host pytest runs when Docker is off (default ON); "
                "set ARBITER_ALLOW_HOST_TESTS=false to turn that off.\n"
            )

    if client is not None:
        try:
            print(f"  Mounting volume: {abs_repo_path} -> /app")
            print(f"  Running pytest in Docker image {image}")

            container = client.containers.run(
                image,
                command=command,
                volumes={abs_repo_path: {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                detach=True,
                stdout=True,
                stderr=True,
            )

            result = container.wait(timeout=300)
            exit_code = result.get("StatusCode", 1)
            raw_logs = container.logs(stdout=True, stderr=True)
            container_logs = raw_logs.decode("utf-8", errors="replace")
            host_only = False

            try:
                container.remove()
            except Exception:
                pass

        except docker.errors.ContainerError as e:
            container_logs = (
                e.stderr.decode("utf-8", errors="replace") if e.stderr else str(e)
            )
            exit_code = 1
            host_only = False
        except Exception as e:
            if stack == "PYTHON" and _env_truthy("ARBITER_ALLOW_HOST_TESTS", True):
                print(f"  Docker run failed ({e}); trying host pytest…")
                container_logs, exit_code = _run_pytest_on_host(abs_repo_path)
                host_only = True
            else:
                container_logs = f"Docker Execution Failed: {str(e)}"
                exit_code = 1

    if exit_code == 5 and stack == "PYTHON":
        print("  Pytest Exit Code 5 (No Tests Found). Attempting fallback: python main.py")
        if host_only:
            fb_logs, fb_exit = _run_python_main_on_host(abs_repo_path)
            if fb_exit != 0:
                print(f"  Fallback 'python main.py' FAILED. Exit Code: {fb_exit}")
                exit_code = fb_exit
                container_logs += f"\n\n[HOST FALLBACK EXECUTION: python main.py]\nEXIT CODE: {fb_exit}\nLOGS:\n{fb_logs}"
            else:
                print("  Fallback 'python main.py' PASSED.")
                container_logs += f"\n\n[HOST FALLBACK EXECUTION: python main.py]\nSUCCESS. Output:\n{fb_logs}"
                exit_code = 0
        else:
            try:
                fallback_command = "bash -c 'python main.py 2>&1'"
                fb_container = client.containers.run(
                    image,
                    command=fallback_command,
                    volumes={abs_repo_path: {"bind": "/app", "mode": "rw"}},
                    working_dir="/app",
                    detach=True,
                )
                fb_result = fb_container.wait(timeout=60)
                fb_exit_code = fb_result.get("StatusCode", 1)
                fb_logs = fb_container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                try:
                    fb_container.remove()
                except Exception:
                    pass

                if fb_exit_code != 0:
                    print(f"  Fallback 'python main.py' FAILED. Exit Code: {fb_exit_code}")
                    exit_code = fb_exit_code
                    container_logs += f"\n\n[FALLBACK EXECUTION: python main.py]\nEXIT CODE: {fb_exit_code}\nLOGS:\n{fb_logs}"
                else:
                    print("  Fallback 'python main.py' PASSED.")
                    container_logs += f"\n\n[FALLBACK EXECUTION: python main.py]\nSUCCESS. Output:\n{fb_logs}"
                    exit_code = 0

            except Exception as fb_e:
                container_logs += f"\n\nFallback execution failed: {str(fb_e)}"

    timeline = state.get("timeline", [])
    timeline.append(
        {
            "timestamp": datetime.now().isoformat(),
            "event": "TEST_RUN",
            "details": {
                "exit_code": exit_code,
                "retry_count": state.get("retry_count", 0),
            },
        }
    )

    def _clean_logs(raw: str) -> str:
        skip_prefixes = (
            "WARNING: Running pip",
            "[notice]",
            "Defaulting to user installation",
        )
        lines = [
            l
            for l in raw.splitlines()
            if not any(l.strip().startswith(p) for p in skip_prefixes)
        ]
        return "\n".join(lines).strip()

    clean_logs = _clean_logs(container_logs)
    state["error_logs"] = clean_logs
    state["timeline"] = timeline

    failed_count = 0
    match = re.search(r"=== (\d+) failed", clean_logs)
    if match:
        failed_count = int(match.group(1))

    failure_history = state.get("failure_history", [])
    failure_history.append(failed_count)
    state["failure_history"] = failure_history
    state["failure_count"] = failed_count

    current_score, _, _, _, _ = calculate_score(state)
    print(f"    Current Score: {current_score} (Pass Threshold: >=100)")

    if current_score >= 100:
        state["final_status"] = "PASSED"
        state["is_healing_complete"] = True
    else:
        state["final_status"] = "FAILED"
        state["retry_count"] = state.get("retry_count", 0) + 1

    state["current_step"] = "TESTING_COMPLETE"
    state["last_exit_code"] = exit_code

    print(f"Testing Complete. Exit Code: {exit_code}")
    print(f"Stats: {failed_count} Failed. History: {failure_history}")
    print(f"Logs:\n{clean_logs[:800]}{'...' if len(clean_logs) > 800 else ''}")

    return state
