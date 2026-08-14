import streamlit as st

def render_code_editor(starter_code: str, key: str = "code_editor") -> str:
    """
    Render a code editor text area with syntax highlighting.
    
    Args:
        starter_code: Initial code to populate in the editor
        key: Unique key for the Streamlit widget
    
    Returns:
        User-entered code string
    """
    # Get current code from session state or use starter code
    current_code = st.session_state.get("current_code", starter_code)
    
    # Use text_area with code highlighting
    user_code = st.text_area(
        label="📝 Write Your Solution",
        value=current_code,
        height=350,
        key=key,
        help="Write your Python solution here. The function should accept input and return output.",
    )
    
    # Update session state with current code
    if user_code != st.session_state.get("current_code"):
        st.session_state["current_code"] = user_code
    
    return user_code

def render_code_editor_readonly(code: str) -> None:
    """
    Render a read-only code display (for viewing opponent's code).
    
    Args:
        code: Code to display
    """
    st.code(code, language="python")

def render_code_editor_with_tabs(
    starter_code: str,
    submitted_code: str,
    opponent_code: str = None,
    key_prefix: str = "editor"
) -> tuple[str, bool]:
    """
    Render a tabbed code editor with multiple views.
    
    Args:
        starter_code: Problem's starter code
        submitted_code: User's submitted code
        opponent_code: Opponent's submitted code (optional)
        key_prefix: Prefix for Streamlit widget keys
    
    Returns:
        Tuple of (current_code, was_submitted)
    """
    tabs = st.tabs(["✏️ Editor", "📤 Submitted", "👥 Opponent"])
    
    current_code = starter_code
    was_submitted = False
    
    # Tab 1: Code Editor
    with tabs[0]:
        current_code = render_code_editor(starter_code, key=f"{key_prefix}_main")
    
    # Tab 2: My Submission
    with tabs[1]:
        if submitted_code:
            render_code_editor_readonly(submitted_code)
            st.success("✅ You have submitted this code")
        else:
            st.info("You haven't submitted any code yet.")
    
    # Tab 3: Opponent's Code
    with tabs[2]:
        if opponent_code:
            render_code_editor_readonly(opponent_code)
        else:
            st.info("Opponent hasn't submitted yet or you're viewing this in the lobby.")
    
    return current_code, was_submitted

def render_code_stats(code: str) -> dict:
    """
    Calculate basic statistics about the code.
    
    Args:
        code: Python code string
    
    Returns:
        Dictionary with code statistics
    """
    lines = code.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    stats = {
        "total_lines": len(lines),
        "code_lines": len(non_empty_lines),
        "characters": len(code),
        "has_function": "def " in code,
    }
    
    return stats

def render_code_editor_with_stats(starter_code: str, key: str = "code_editor") -> str:
    """
    Render code editor with real-time statistics.
    
    Args:
        starter_code: Initial code for the editor
        key: Unique widget key
    
    Returns:
        User-entered code
    """
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_code = render_code_editor(starter_code, key)
    
    with col2:
        if user_code:
            stats = render_code_stats(user_code)
            st.markdown("#### 📊 Code Stats")
            st.metric("Lines", stats["code_lines"])
            st.metric("Chars", stats["characters"])
            if stats["has_function"]:
                st.success("✅ Has function")
            else:
                st.warning("⚠️ No function")
    
    return user_code

if __name__ == "__main__":
    print("Editors Component Module - Testing interface")
    print("render_code_editor(starter_code): Renders code editor text area")
    print("render_code_editor_readonly(code): Displays read-only code")
    print("render_code_editor_with_tabs(...): Tabbed editor with multiple views")
    print("render_code_stats(code): Calculates code statistics")
    print("render_code_editor_with_stats(...): Editor with real-time stats")
