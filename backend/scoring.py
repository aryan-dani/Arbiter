from datetime import datetime
from backend.state import AgentState

def calculate_score(state: AgentState) -> int:
    """
    Calculates the final score based on performance.
    Base 100
    +10 speed bonus (if < 5 mins)
    -2 penalty for every commit over 20 (Wait, prompt says 'every commit over 20'. '20' seems high for a healing loop, maybe it meant total commits? Or maybe if iterations > ...? 
    "Base 100, +10 speed bonus (if < 5 mins), and -2 penalty for every commit over 20"
    Assumed "commit over 20" means if commits > 20, penalty applies. 
    Actually, let's re-read carefully: "-2 penalty for every commit over 20". 
    This implies if I have 21 commits, I get -2. If 22, -4? Or is it "-2 penalty for every commit" (if total > 20)?
    Given the context of a hackathon, and "healing", usually you don't do 20 commits. 
    Maybe it means "-2 penalty for every commit" (total). Or maybe "penalty for every commit over the threshold of 20"?
    I will assume it means: `if total_commits > 20: penalty = (total_commits - 20) * 2`. 
    BUT, looking at typical hackathon rules, maybe it means "-2 for each commit" generally? No, that punishes fixing.
    "every commit over 20". I'll stick to the threshold interpretation.
    """
    base_score = 100
    
    # Calculate Time
    # Duration is now calculated by comparing current time with start_time in state
    start_time_ts = state.get('start_time')
    if start_time_ts:
        duration = datetime.now().timestamp() - start_time_ts
    else:
        duration = state.get('total_time', 0.0) # Fallback

    if duration < 300: # 5 mins
        base_score += 10
        
    # Calculate Commits
    # fixes_applied list len is the number of commits (1 fix = 1 commit in our logic)
    commit_count = len(state.get('fixes_applied', []))
    
    if commit_count > 20:
        penalty = (commit_count - 20) * 2
        base_score -= penalty
        
    return max(0, base_score), duration

def scoring_node(state: AgentState) -> AgentState:
    """
    Final node to calculate score and wrap up.
    """
    # Calculate total time if not set (assuming start time was tracked externally or we track it here)
    # We didn't track start_time in state explicitly in discovery.
    # We should have. Let's add it or assume main.py handles it? 
    # main.py sets start_time. We need to pass it in or calculate delta.
    # For now, let's just use a placeholder or assume `total_time` is updated.
    
    # Let's assume we update total_time here relative to some start. 
    # But state is typeddict. 
    # simpler: just use 0 if not set, or modify main.py to pass start_timestamp.
    
    score, duration = calculate_score(state)
    state['final_score'] = score
    state['total_time'] = duration
    print(f"Final Score: {score}, Duration: {duration:.2f}s")
    return state
