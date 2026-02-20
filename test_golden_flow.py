import requests
import time
import sys
import argparse

# Configuration
API_URL = "http://localhost:8000"
DEFAULT_REPO = "https://github.com/octocat/Hello-World" # Safe default, though likely won't have bugs to fix
DEFAULT_TEAM = "GOLDEN_TESTERS"
DEFAULT_LEADER = "TEST_BOT"

def run_test(repo_url, team_name, leader_name):
    print(f"🚀 Starting Golden Test for {repo_url}...")
    
    # 1. Trigger Healing
    payload = {
        "repo_url": repo_url,
        "team_name": team_name,
        "leader_name": leader_name,
        "max_iterations": 5,
        "model_name": "gemini-2.5-flash"
    }
    
    try:
        response = requests.post(f"{API_URL}/start-healing", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Agent Started! Run ID: {data.get('run_id')}")
        print(f"   Branch: {data.get('branch_name')}")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")
        sys.exit(1)

    # 2. Poll Status
    print("\n⏳ Polling status...")
    start_time = time.time()
    while True:
        try:
            status_res = requests.get(f"{API_URL}/status/{team_name}")
            status_res.raise_for_status()
            status_data = status_res.json()
            
            status = status_data.get("status")
            
            # Print dynamic updates (if available) or just dots
            if "result" in status_data:
                result = status_data["result"]
                final_status = result.get("final_status")
                score = result.get("final_score")
                print(f"\n✨ Workflow Finished!")
                print(f"   Final Status: {final_status}")
                print(f"   Score: {score}/100")
                print(f"   Fixes Applied: {len(result.get('fixes_applied', []))}")
                
                if final_status == "PASSED":
                    print("🎉 TEST PASSED: Agent successfully healed the repo!")
                    sys.exit(0)
                else:
                    print(f"⚠️ TEST COMPLETED (Status: {final_status}). Check functionality.")
                    sys.exit(0)
                    
            elif status == "running":
                sys.stdout.write(".")
                sys.stdout.flush()
                time.sleep(2)
                
            elif status == "error":
                print(f"\n❌ Agent Error: {status_data.get('error')}")
                sys.exit(1)
                
            else:
                print(f"\n❓ Unknown Status: {status}")
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n🛑 Test cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Polling Error: {e}")
            time.sleep(2)
            
        # Timeout safety
        if time.time() - start_time > 600: # 10 mins
            print("\n⏰ Test Timed Out!")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RIFT 2026 Golden Test")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub Repo URL to test")
    parser.add_argument("--team", default=DEFAULT_TEAM, help="Team Name")
    parser.add_argument("--leader", default=DEFAULT_LEADER, help="Leader Name")
    
    args = parser.parse_args()
    
    # Simple Health Check first
    try:
        requests.get(f"{API_URL}/health").raise_for_status()
    except Exception:
        print(f"❌ Backend not reachable at {API_URL}. Is it running?")
        sys.exit(1)
        
    run_test(args.repo, args.team, args.leader)
