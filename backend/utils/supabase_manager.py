import os
from datetime import datetime
import json
from supabase import create_client, Client
from typing import Optional, Dict, Any

class SupabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if url and key:
            self.client: Client = create_client(url, key)
            self.enabled = True
        else:
            print("WARNING: SUPABASE_URL or SUPABASE_KEY not found. Real-time logging disabled.")
            self.client = None
            self.enabled = False

    def create_run(self, run_name: str, target_repo: str) -> Optional[str]:
        """Creates a new run entry and returns the run_id."""
        if not self.enabled:
            return None
        
        try:
            data = {
                "run_name": run_name,
                "target_repo": target_repo,
                "status": "PENDING",
                "created_at": datetime.utcnow().isoformat()
            }
            response = self.client.table("agent_runs").insert(data).execute()
            if response.data:
                return response.data[0]['id']
        except Exception as e:
            print(f"Supabase Error (create_run): {e}")
        return None

    def update_node_status(self, run_id: str, node: str, log_type: str, content: Dict[str, Any]):
        """Logs a node event."""
        if not self.enabled or not run_id:
            return

        try:
            data = {
                "run_id": run_id,
                "node_name": node,
                "log_type": log_type,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            self.client.table("node_logs").insert(data).execute()
        except Exception as e:
            print(f"Supabase Error (update_node_status): {e}")

    def finalize_run(self, run_id: str, score: int, duration: float, status: str):
        """Updates the final status of a run."""
        if not self.enabled or not run_id:
            return

        try:
            data = {
                "final_score": score,
                "duration": duration,
                "status": status
            }
            self.client.table("agent_runs").update(data).eq("id", run_id).execute()
        except Exception as e:
            print(f"Supabase Error (finalize_run): {e}")

    def get_previous_fix(self, bug_type: str, description: str) -> Optional[Dict[str, Any]]:
        """
        Searches for a successful fix for a similar bug from previous runs.
        Returns the fix details if found.
        """
        if not self.enabled:
            return None

        # Basic similarity search (could be improved with embeddings later)
        # For now, we look for logs where log_type='FIX_APPLIED' and content->bug_type matches
        try:
            response = self.client.table("node_logs") \
                .select("content") \
                .eq("log_type", "FIX_APPLIED") \
                .execute()
            
            # Application-side filtering (naive)
            # In a real vector DB, we'd do semantic search.
            # Here we just look for exact bug_type match and partial description match.
            best_fix = None
            
            for row in response.data:
                content = row.get('content', {})
                if content.get('bug_type') == bug_type:
                    # Check text similarity roughly
                    past_desc = content.get('description', '').lower()
                    curr_desc = description.lower()
                    
                    # If considerable overlap in description words
                    past_words = set(past_desc.split())
                    curr_words = set(curr_desc.split())
                    common = past_words.intersection(curr_words)
                    
                    if len(common) / max(len(curr_words), 1) > 0.5:
                        best_fix = content
                        break
            
            return best_fix

        except Exception as e:
            print(f"Supabase Error (get_previous_fix): {e}")
            return None
