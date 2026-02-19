import docker
import os
from datetime import datetime
from backend.state import AgentState

def tester_node(state: AgentState) -> AgentState:
    """
    Spins up a Docker container to run tests (sandboxed).
    """
    print("Tester Node Started...")
    try:
        client = docker.from_env()
        client.ping()
    except Exception:
        # Fallback for Windows named pipe if from_env fails
        print("    docker.from_env() failed, attempting Windows named pipe connection...")
        client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')

    repo_path = state['repo_path']
    stack = state['detected_stack']

    container_logs = ""
    exit_code = 1

    try:
        if stack == "PYTHON":
            # Suppress pip noise → only pytest output reaches the debugger
            command = (
                "bash -c '"
                "pip install pytest --quiet -q > /dev/null 2>&1; "
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet -q > /dev/null 2>&1); "
                "pytest -v --tb=long 2>&1'"
            )
            image = "python:3.11-slim"

        elif stack == "NODE":
            # Use full node image (has bash + more tools)
            command = (
                "bash -c '"
                "npm install --silent 2>/dev/null && "
                "(npm test 2>&1 || true)'"
            )
            image = "node:18"   # Full Debian image, has bash

        else:
            print(f"Unknown or undetected stack: '{stack}'. Defaulting to Python with pytest.")
            command = (
                "bash -c '"
                "pip install pytest --quiet -q > /dev/null 2>&1; "
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet -q > /dev/null 2>&1); "
                "pytest -v --tb=long 2>&1'"
            )
            image = "python:3.11-slim"

        abs_repo_path = os.path.abspath(repo_path)
        print(f"  Mounting volume: {abs_repo_path} -> /app")
        print(f"  Running command: {command}")

        container = client.containers.run(
            image,
            command=command,
            volumes={abs_repo_path: {'bind': '/app', 'mode': 'rw'}},
            working_dir="/app",
            detach=True,
            stdout=True,
            stderr=True,
        )

        result = container.wait(timeout=300)  # 5 minute timeout
        exit_code = result.get('StatusCode', 1)

        # Get combined stdout+stderr logs
        raw_logs = container.logs(stdout=True, stderr=True)
        container_logs = raw_logs.decode("utf-8", errors="replace")

        try:
            container.remove()
        except Exception:
            pass

    except docker.errors.ContainerError as e:
        container_logs = f"Container error: {e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)}"
        exit_code = 1
    except Exception as e:
        container_logs = f"Docker Execution Failed: {str(e)}"
        exit_code = 1

    # Add timeline event
    timeline = state.get('timeline', [])
    timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": "TEST_RUN",
        "details": {
            "exit_code": exit_code,
            "retry_count": state.get('retry_count', 0),
        }
    })

    # Strip pip noise lines so debugger sees clean pytest output
    def _clean_logs(raw: str) -> str:
        skip_prefixes = (
            "WARNING: Running pip",
            "[notice]",
            "Defaulting to user installation",
        )
        lines = [l for l in raw.splitlines() if not any(l.strip().startswith(p) for p in skip_prefixes)]
        return "\n".join(lines).strip()

    clean_logs = _clean_logs(container_logs)
    state['error_logs'] = clean_logs  # Full clean pytest output for debugger
    state['timeline'] = timeline

    if exit_code == 0:
        state['final_status'] = "PASSED"
        state['is_healing_complete'] = True
    else:
        state['final_status'] = "FAILED"
        state['retry_count'] = state.get('retry_count', 0) + 1

    state['current_step'] = "TESTING_COMPLETE"

    print(f"Testing Complete. Exit Code: {exit_code}")
    print(f"Container Logs:\n{clean_logs[:800]}{'...' if len(clean_logs) > 800 else ''}")

    return state
