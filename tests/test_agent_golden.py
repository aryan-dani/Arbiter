
import pytest
from backend.main import run_healing_workflow, HealingRequest
import asyncio

# This test assumes the backend is running and can access the internet.
# Ideally, we would mock the GitHub/Gemini APIs, but for a "Golden Test" 
# we want to verify the E2E flow against a real (but controlled) repo.

# Repo: https://github.com/aryan-dani/rift-test-buggy-repo
# Contains a simple Python error (buggy_calculator.py)

@pytest.mark.asyncio
async def test_end_to_end_healing():
    team_name = "GOLDEN_TEST_BOT"
    request = HealingRequest(
        repo_url="https://github.com/aryan-dani/rift-test-buggy-repo",
        team_name=team_name,
        leader_name="Tester"
    )
    
    print(f"\n[Golden Test] Starting E2E healing run for {team_name}...")
    
    try:
        await run_healing_workflow(request)
        print("[Golden Test] Workflow execution finished.")
    except Exception as e:
        pytest.fail(f"Workflow crashed during execution: {e}")
        
    # Validation: Check results.json for the latest entry for this team
    import os
    import json
    
    # Path to results.json in project root
    results_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results.json")
    
    assert os.path.exists(results_path), "results.json was not created/found"
    
    with open(results_path, "r") as f:
        results = json.load(f)
        
    # Find the most recent entry for our golden test bot
    my_runs = [r for r in results if r.get('team_name') == team_name]
    assert len(my_runs) > 0, f"No results found for {team_name} in results.json"
    
    latest_run = my_runs[-1]
    status = latest_run.get('final_status')
    score = latest_run.get('final_score')
    
    print(f"[Golden Test] Final Status: {status}, Score: {score}")
    
    # Assert successful healing
    assert status == "PASSED", f"Golden test failed to heal the repo. Status: {status}"
    assert score > 0, "Score should be greater than 0 for a PASSED run"
    print("[Golden Test] VERIFIED: Repo successfully healed.")
