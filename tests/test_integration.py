import pytest
import os
import json
from unittest.mock import MagicMock, patch
from backend.graph import create_workflow
from backend.state import AgentState

# Path to dummy repo inside the project but ignored
DUMMY_REPO_PATH = os.path.abspath("temp_dummy_repo")

from dotenv import load_dotenv
load_dotenv("backend/.env")

@pytest.mark.asyncio
async def test_healing_loop():
    # Setup: Ensure dummy repo exists (just the directory structure needed for discovery node potentially, or we mock that too?)
    # Discovery node uses os.path.exists checks. We can try to keep the dummy repo existing or mock discovery too.
    # The prompt says "Constraint: Do not rely on writing to calc.py inside the dummy repo".
    # But Discovery node clones/checks files.
    # Let's ensure the dir exists at least.
    if not os.path.exists(DUMMY_REPO_PATH):
        os.makedirs(DUMMY_REPO_PATH, exist_ok=True)
        # Create a dummy file so Discovery sees it as a Python stack
        with open(os.path.join(DUMMY_REPO_PATH, "main.py"), "w") as f:
            f.write("# dummy")

    # Mock specific AI responses
    mock_debugger_response = MagicMock()
    mock_debugger_response.text = json.dumps({
        "file": "calc.py",
        "line": 2,
        "bug_type": "LOGIC",
        "description": "Subtraction used instead of addition"
    })
    
    # Mock Fixer response - strictly code
    mock_fixer_response = MagicMock()
    mock_fixer_response.text = "def add(a, b):\n    return a + b"
    
    with patch("backend.nodes.tester.docker.from_env") as MockDocker, \
         patch("google.genai.Client") as MockClient, \
         patch("backend.nodes.discovery.Repo") as MockRepoDiscovery, \
         patch("backend.nodes.git_node.Repo") as MockRepoCommit:
        
        # Setup Docker Mocks
        mock_client = MockDocker.return_value
        mock_container = MagicMock()
        mock_client.containers.run.return_value = mock_container
        
        # Scenario: 
        # 1. First run -> Fails (Exit Code 1)
        # 2. Second run -> Passes (Exit Code 0)
        mock_container.wait.side_effect = [
            {'StatusCode': 1}, # First run
            {'StatusCode': 0}  # Second run
        ]
        
        mock_container.logs.side_effect = [
            b"AssertionError: assert 2 - 3 == 5", # First run logs
            b"Tests Passed!"                       # Second run logs
        ]
        
        # Setup AI Mocks
        mock_genai_client = MockClient.return_value
        mock_genai_client.models.generate_content.side_effect = [
            mock_debugger_response, # Debugger
            mock_fixer_response     # Fixer
        ]

        # Setup Discovery Mock (Mock the clone to just create files)
        def side_effect_clone(url, to_path):
            os.makedirs(to_path, exist_ok=True)
            # Create dummy files in to_path for detection
            with open(os.path.join(to_path, "requirements.txt"), "w") as f:
                f.write("pytest")
            with open(os.path.join(to_path, "calc.py"), "w") as f:
                f.write("def add(a, b):\n    return a - b") 
            with open(os.path.join(to_path, "test_calc.py"), "w") as f:
                f.write("def test_add(): pass")
            return MagicMock()

        MockRepoDiscovery.clone_from.side_effect = side_effect_clone

        # Setup Git Commit Mock
        mock_repo_instance = MockRepoCommit.return_value
        mock_repo_instance.active_branch.name = "main"
        mock_repo_instance.heads = []
        mock_repo_instance.create_head.return_value.checkout.return_value = None
        mock_repo_instance.is_dirty.return_value = True 
        
        import datetime
        
        # Setup Initial State
        initial_state = AgentState(
            repo_url=DUMMY_REPO_PATH, 
            team_name="TestTeam",
            leader_name="TestLeader",
            repo_path="",
            start_time=datetime.datetime.now().timestamp(),
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
            today=""
        )
        
        app = create_workflow()
        
        print("Starting Workflow Execution with Mocks...")
        final_state = await app.ainvoke(initial_state)
        
        print("Workflow Finished.")
        print(f"Final Status: {final_state.get('final_status')}")
        print(f"Score: {final_state.get('final_score')}")
        print(f"Fixes: {final_state.get('fixes_applied')}")
        
        # Assertions
        assert final_state['final_status'] == "PASSED"
        assert len(final_state['fixes_applied']) == 1
        assert final_state['fixes_applied'][0]['bug_type'] == "LOGIC"
        assert final_state['final_score'] > 0
