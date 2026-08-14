import streamlit as st

def render_match_creation_form() -> dict | None:
    """
    Render the match creation form in the lobby.
    
    Returns:
        Dictionary with form data (difficulty) or None if not submitted
    """
    st.markdown("## 🎮 Create a New Match")
    
    with st.form("match_creation_form"):
        # Difficulty selector
        difficulty = st.selectbox(
            label="Select Difficulty",
            options=["easy", "medium", "hard"],
            index=1,  # Default to medium
            help="Choose the difficulty level for the problem",
            key="difficulty_selector"
        )
        
        # Difficulty descriptions
        difficulty_info = {
            "easy": "Simple algorithms, basic data structures",
            "medium": "Moderate complexity, common interview questions",
            "hard": "Complex algorithms, optimization challenges"
        }
        st.caption(f"💡 *{difficulty_info.get(difficulty, '')}*")
        
        st.markdown("---")
        
        # Create button
        submitted = st.form_submit_button(
            label="🚀 Create Match",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            return {"difficulty": difficulty}
    
    return None

def render_submission_form(starter_code: str, key: str = "submission") -> tuple[str, bool]:
    """
    Render the code submission form in the arena.
    
    Args:
        starter_code: Problem's starter code
        key: Unique key for the form
    
    Returns:
        Tuple of (user_code, was_submitted)
    """
    # Import the code editor
    from components.editors import render_code_editor_with_stats
    
    st.markdown("### 📤 Submit Your Solution")
    
    with st.form(key):
        # Code editor
        user_code = render_code_editor_with_stats(
            starter_code,
            key=f"{key}_editor"
        )
        
        # Info about scoring
        st.caption("""
        💡 **Scoring:**
        - Test case pass rate: up to 100 points
        - AI bonus score: 0-10 points
        - Total = Test Score + AI Bonus
        """)
        
        st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button(
            label="⚡ Run & Evaluate",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            if not user_code or not user_code.strip():
                st.error("❌ Please enter some code before submitting!")
                return user_code, False
            
            if "def " not in user_code:
                st.warning("⚠️ Your code doesn't seem to define a function!")
                return user_code, False
            
            return user_code, True
    
    # If not submitted, return current code and False
    return user_code, False

def render_difficulty_selector(key: str = "difficulty") -> str:
    """
    Render a standalone difficulty selector.
    
    Args:
        key: Unique key for the widget
    
    Returns:
        Selected difficulty string
    """
    difficulty = st.selectbox(
        label="Select Difficulty",
        options=["easy", "medium", "hard"],
        index=1,
        key=key
    )
    
    return difficulty

def render_match_url_display(match_id: str) -> None:
    """
    Render the match URL with copy button.
    
    Args:
        match_id: The Firestore match ID
    """
    # Get the current URL
    try:
        # Try to get from query params first
        query_params = st.experimental_get_query_params()
        # This would need JavaScript for clipboard functionality
        # For now, display the URL in a code block
        share_url = f"?match_id={match_id}"
        
        st.markdown("### 🔗 Share This Match")
        st.code(share_url, language="text")
        st.caption("Copy this URL and share it with your opponent!")
        
    except Exception as e:
        st.error(f"Could not generate share URL: {e}")

def render_poll_status(last_update: str, match_status: str) -> None:
    """
    Render polling status indicator.
    
    Args:
        last_update: Timestamp of last update
        match_status: Current match status
    """
    status_indicators = {
        "waiting": ("⏳", "Waiting for opponent...", "orange"),
        "active": ("⚔️", "Match in progress!", "green"),
        "finished": ("🏆", "Match finished!", "purple")
    }
    
    emoji, message, color = status_indicators.get(
        match_status, 
        ("❓", "Unknown status", "gray")
    )
    
    st.markdown(
        f"""
        <div style="
            padding: 10px; 
            border-radius: 5px; 
            background-color: {color}20;
            border: 1px solid {color};
            text-align: center;
        ">
            <span style="font-size: 24px;">{emoji}</span><br>
            <span>{message}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    print("Forms Component Module - Testing interface")
    print("render_match_creation_form(): Renders match creation form")
    print("render_submission_form(starter_code): Renders code submission form")
    print("render_difficulty_selector(): Renders standalone difficulty selector")
    print("render_match_url_display(match_id): Shows shareable match URL")
    print("render_poll_status(last_update, match_status): Shows polling status")
