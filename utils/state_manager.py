import streamlit as st

def init_session_state() -> None:
    """
    Initialize Streamlit session state with default values.
    
    This should be called at the beginning of app.py to ensure
    all session variables are properly initialized.
    """
    # Player and match identification
    st.session_state.setdefault("player_id", None)  # "p1" or "p2"
    st.session_state.setdefault("match_id", None)   # Firestore match ID
    
    # Match creation state
    st.session_state.setdefault("difficulty", "medium")  # Selected difficulty
    
    # Player action state
    st.session_state.setdefault("submitted", False)  # Whether player has submitted
    st.session_state.setdefault("submitted_code", "")  # Last submitted code
    st.session_state.setdefault("current_code", "")  # Current editor content
    
    # Results and scoring
    st.session_state.setdefault("last_results", [])  # Last test results
    st.session_state.setdefault("last_score", 0)  # Last calculated score
    st.session_state.setdefault("last_ai_review", {})  # Last AI review data
    
    # UI state
    st.session_state.setdefault("auto_refresh", True)  # Enable auto-refresh
    st.session_state.setdefault("view_mode", "problem")  # "problem" or "results"
    
    # Match polling
    st.session_state.setdefault("last_poll_time", 0)  # Timestamp of last poll
    st.session_state.setdefault("poll_interval", 3)  # Seconds between polls

def update_player_state(player_id: str, match_id: str) -> None:
    """
    Update session state with current player and match info.
    
    Args:
        player_id: "p1" or "p2"
        match_id: Firestore match ID
    """
    st.session_state["player_id"] = player_id
    st.session_state["match_id"] = match_id

def clear_match_state() -> None:
    """
    Clear match-specific state to allow starting a new match.
    """
    # Clear match-related state but keep preferences
    st.session_state["player_id"] = None
    st.session_state["match_id"] = None
    st.session_state["submitted"] = False
    st.session_state["submitted_code"] = ""
    st.session_state["current_code"] = ""
    st.session_state["last_results"] = []
    st.session_state["last_score"] = 0
    st.session_state["last_ai_review"] = {}

def update_submission_state(code: str, results: list, score: int, ai_review: dict) -> None:
    """
    Update state after code submission.
    
    Args:
        code: Submitted code
        results: Test case results
        score: Calculated score
        ai_review: AI review data
    """
    st.session_state["submitted"] = True
    st.session_state["submitted_code"] = code
    st.session_state["current_code"] = code
    st.session_state["last_results"] = results
    st.session_state["last_score"] = score
    st.session_state["last_ai_review"] = ai_review

def reset_submission_state() -> None:
    """
    Reset submission state for a new attempt.
    """
    st.session_state["submitted"] = False
    st.session_state["last_results"] = []
    st.session_state["last_score"] = 0
    st.session_state["last_ai_review"] = {}

def get_player_display_name() -> str:
    """
    Get display name for current player.
    
    Returns:
        "Player 1", "Player 2", or "Unknown"
    """
    player_id = st.session_state.get("player_id")
    if player_id == "p1":
        return "Player 1"
    elif player_id == "p2":
        return "Player 2"
    else:
        return "Unknown"

def get_opponent_display_name() -> str:
    """
    Get display name for opponent.
    
    Returns:
        "Player 1", "Player 2", or "Unknown"
    """
    player_id = st.session_state.get("player_id")
    if player_id == "p1":
        return "Player 2"
    elif player_id == "p2":
        return "Player 1"
    else:
        return "Unknown"

def should_refresh() -> bool:
    """
    Check if it's time to refresh based on polling interval.
    
    Returns:
        True if should refresh, False otherwise
    """
    import time
    
    if not st.session_state.get("auto_refresh", True):
        return False
    
    current_time = time.time()
    last_poll = st.session_state.get("last_poll_time", 0)
    interval = st.session_state.get("poll_interval", 3)
    
    if current_time - last_poll > interval:
        st.session_state["last_poll_time"] = current_time
        return True
    
    return False

def get_shareable_url(match_id: str) -> str:
    """
    Generate a shareable URL for a match.
    
    Args:
        match_id: Firestore match ID
    
    Returns:
        Shareable URL with match_id parameter
    """
    import urllib.parse
    
    # For Streamlit Cloud deployment, use relative URL
    # In production, this would be the deployed app URL
    base_url = st.experimental_get_query_params().get("base_url", ["/"])[0]
    
    # Create query parameters
    params = {"match_id": match_id}
    query_string = urllib.parse.urlencode(params)
    
    return f"{base_url}?{query_string}"

if __name__ == "__main__":
    # Test the module
    print("State Manager Module - Testing interface")
    print("init_session_state(): Initializes all session variables")
    print("update_player_state('p1', 'clash_abc123'): Sets player and match")
    print("clear_match_state(): Clears match-specific state")
    print("update_submission_state(...): Updates after submission")
    print("get_player_display_name(): Returns 'Player 1', 'Player 2', or 'Unknown'")
    print("should_refresh(): Returns True/False based on polling interval")
    print("get_shareable_url('clash_abc123'): Returns shareable match URL")
