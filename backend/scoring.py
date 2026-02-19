from datetime import datetime
from backend.state import AgentState

def calculate_score(state: AgentState) -> tuple[int, float, int, int, int]:
    """
    Calculates the final score based on performance.
    Base 100, +10 speed bonus (if < 5 mins), and -2 penalty for every commit over 20.
    Returns (final_score, duration, base_score, speed_bonus, efficiency_penalty)
    """
    if state.get('final_status') != "PASSED":
        # Any failure results in a 0 score
        duration = state.get('total_time', 0.0)
        start_time_ts = state.get('start_time')
        if start_time_ts and duration == 0:
            duration = datetime.now().timestamp() - start_time_ts
        return 0, duration, 0, 0, 0

    base_score = 100
    
    # Calculate Time
    duration = state.get('total_time', 0.0)
    start_time_ts = state.get('start_time')
    if start_time_ts and duration == 0:
        duration = datetime.now().timestamp() - start_time_ts

    speed_bonus = 10 if duration < 300 else 0
    
    # Calculate Commits
    fixes = state.get('fixes_applied', [])
    commit_count = len(fixes)
    efficiency_penalty = max(0, (commit_count - 20) * 2) if commit_count > 20 else 0
        
    final_score = max(0, base_score + speed_bonus - efficiency_penalty)
    return final_score, duration, base_score, speed_bonus, efficiency_penalty

def scoring_node(state: AgentState) -> AgentState:
    """
    Final node to calculate score and wrap up.
    """
    score, duration, base_score, speed_bonus, penalty = calculate_score(state)
    
    state['final_score'] = score
    state['total_time'] = duration
    
    # Store breakdown in state for results.json logging consistency
    state['current_analysis']['scoring_breakdown'] = {
        "base_score": base_score,
        "speed_bonus": speed_bonus,
        "efficiency_penalty": penalty
    }

    print(f"Scoring Complete. Final Score: {score}, Duration: {duration:.2f}s")
    return state
