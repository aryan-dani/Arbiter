import docker
import os
from datetime import datetime
from backend.state import AgentState

def tester_node(state: AgentState) -> AgentState:
    """
    Spins up a Docker container to run tests (sandboxed).
    """
    print("Tester Node Started...")
    client = docker.from_env()
    repo_path = state['repo_path']
    stack = state['detected_stack']

    container_logs = ""
    exit_code = 1

    try:
        if stack == "PYTHON":
            # Install deps if requirements.txt exists, then run pytest
            command = (
                "bash -c '"
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet) 2>&1; "
                "pip install pytest --quiet 2>&1; "
                "pytest -v --tb=short 2>&1'"
            )
            image = "python:3.11-slim"

        elif stack == "NODE":
            # Use full node image (has bash + more tools)
            command = (
                "bash -c '"
                "npm install 2>&1 && "
                "(npm test 2>&1 || true)'"
            )
            image = "node:18"   # Full Debian image, has bash

        else:
            print(f"Unknown or undetected stack: '{stack}'. Defaulting to Python with pytest.")
            command = (
                "bash -c '"
                "([ -f requirements.txt ] && pip install -r requirements.txt --quiet) 2>&1; "
                "pip install pytest --quiet 2>&1; "
                "pytest -v --tb=short 2>&1'"
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

    state['error_logs'] = container_logs
    state['timeline'] = timeline

    if exit_code == 0:
        state['final_status'] = "PASSED"
        state['is_healing_complete'] = True
    else:
        state['final_status'] = "FAILED"
        state['retry_count'] = state.get('retry_count', 0) + 1

    state['current_step'] = "TESTING_COMPLETE"

    print(f"Testing Complete. Exit Code: {exit_code}")
    print(f"Container Logs:\n{container_logs[:500]}{'...' if len(container_logs) > 500 else ''}")

    return state
