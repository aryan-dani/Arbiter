from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime

class FixDetail(TypedDict):
    path: str
    bug_type: str
    line: int
    description: str
    commit_message: str

class TimelineEvent(TypedDict):
    timestamp: str
    event: str
    details: Optional[Dict[str, Any]]

class AgentState(TypedDict):
    today: str  # just random usage? no, keeping strict to TypedDict
    
    # Input/Context
    repo_url: str
    team_name: str
    leader_name: str
    repo_path: str
    start_time: float # Timestamp
    run_id: Optional[str] # Supabase Run ID
    
    # Forking Support
    upstream_url: str  # The original repo (read-only for agent)
    fork_url: str      # The fork (read/write for agent)

    
    # Execution State
    current_step: str
    retry_count: int
    error_logs: str  # Accumulated logs from tests
    detected_stack: str # Python / Node
    test_files: List[str]
    
    # Results & Metrics
    fixes_applied: List[FixDetail]
    timeline: List[TimelineEvent]
    final_status: str # PASSED / FAILED
    total_time: float # Seconds
    final_score: int
    
    # Control Flow
    is_healing_complete: bool
    current_analysis: Optional[Dict[str, Any]] # Added for passing analysis between nodes
    
    # Rate Limiting
    max_iterations: int
    iterations: int
    model_name: str
