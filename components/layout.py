import streamlit as st
import pandas as pd

def render_header(p1_score: int, p2_score: int, match_status: str) -> None:
    """
    Render the header section with player scores and match status.
    
    Args:
        p1_score: Player 1 score
        p2_score: Player 2 score
        match_status: Current match status
    """
    # Create three columns for the header
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Calculate delta for Player 1
        delta_p1 = p1_score - p2_score if p1_score > p2_score else None
        st.metric(
            label="🎮 Player 1",
            value=p1_score,
            delta=delta_p1
        )
    
    with col2:
        # Determine status color/icon
        status_config = {
            "waiting": {"emoji": "⏳", "color": "orange"},
            "active": {"emoji": "⚔️", "color": "green"},
            "finished": {"emoji": "🏆", "color": "purple"}
        }
        
        config = status_config.get(match_status, {"emoji": "❓", "color": "gray"})
        status_display = f"{config['emoji']} {match_status.title()}"
        
        st.metric(
            label="Match Status",
            value=status_display,
            delta=None
        )
    
    with col3:
        # Calculate delta for Player 2
        delta_p2 = p2_score - p1_score if p2_score > p1_score else None
        st.metric(
            label="🎮 Player 2",
            value=p2_score,
            delta=delta_p2
        )
    
    # Add a separator
    st.divider()

def render_problem_panel(problem_data: dict) -> None:
    """
    Render the problem description panel.
    
    Args:
        problem_data: Dictionary with problem information
    """
    st.markdown(f"# 🎯 {problem_data.get('title', 'Untitled Problem')}")
    st.markdown("---")
    
    # Problem description
    st.markdown("### Problem Description")
    st.markdown(problem_data.get('description', 'No description provided.'))
    
    # Constraints and test cases in expander
    with st.expander("📋 View Constraints & Examples", expanded=True):
        # Constraints
        constraints = problem_data.get('constraints', [])
        if constraints:
            st.markdown("#### Constraints")
            for constraint in constraints:
                st.markdown(f"• {constraint}")
        
        # Test cases
        test_cases = problem_data.get('test_cases', [])
        if test_cases:
            st.markdown("#### Example Test Cases")
            
            # Create a table for test cases
            test_case_data = []
            for i, test_case in enumerate(test_cases[:3]):  # Show max 3 examples
                input_val = test_case.get('input', 'N/A')
                output_val = test_case.get('expected_output', 'N/A')
                
                test_case_data.append({
                    "Case": f"#{i+1}",
                    "Input": str(input_val),
                    "Expected Output": str(output_val)
                })
            
            if test_case_data:
                df = pd.DataFrame(test_case_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Starter code
    starter_code = problem_data.get('starter_code', '')
    if starter_code:
        st.markdown("#### Starter Code")
        st.code(starter_code, language='python')

def render_results(results: list, review_data: dict) -> None:
    """
    Render test results and AI review.
    
    Args:
        results: List of test result dictionaries
        review_data: Dictionary with AI review information
    """
    st.markdown("## 📊 Test Results")
    
    if results:
        # Convert results to DataFrame for display
        df = pd.DataFrame(results)
        
        # Style the Status column
        def color_status(val):
            if "✅" in str(val):
                return 'color: green;'
            elif "❌" in str(val):
                return 'color: red;'
            return ''
        
        # Display styled DataFrame
        st.dataframe(
            df.style.applymap(color_status, subset=['Status']),
            use_container_width=True,
            hide_index=True
        )
        
        # Calculate pass rate
        total_tests = len(results)
        passed_tests = sum(1 for r in results if "✅" in str(r.get('Status', '')))
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        st.markdown(f"**Pass Rate:** {passed_tests}/{total_tests} ({pass_rate:.1f}%)")
    else:
        st.info("No test results available yet.")
    
    # AI Review section
    st.markdown("## 🤖 AI Code Review")
    
    if review_data:
        # Roast review
        roast = review_data.get('roast_review', 'No review available.')
        st.info(f"**Code Roast:** {roast}")
        
        # Complexity analysis
        col1, col2 = st.columns(2)
        with col1:
            time_complexity = review_data.get('time_complexity', 'N/A')
            st.metric(label="⏱️ Time Complexity", value=time_complexity)
        
        with col2:
            space_complexity = review_data.get('space_complexity', 'N/A')
            st.metric(label="💾 Space Complexity", value=space_complexity)
        
        # AI bonus score
        ai_bonus = review_data.get('ai_bonus_score', 0)
        st.progress(ai_bonus / 10, text=f"AI Bonus Score: {ai_bonus}/10")
    else:
        st.info("AI review not available yet.")

def render_match_info(match_id: str, player_name: str) -> None:
    """
    Render match information panel.
    
    Args:
        match_id: Firestore match ID
        player_name: Current player's display name
    """
    with st.sidebar:
        st.markdown("## 📍 Match Info")
        
        # Match ID
        st.markdown(f"**Match ID:** {match_id}")
        
        # Player info
        st.markdown(f"**You are:** {player_name}")
        
        # Copyable share link
        st.markdown("### 📤 Share Match")
        share_text = f"Join my 1v1 Code Clash! Match ID: {match_id}"
        st.code(share_text, language='text')
        
        # QR code for mobile sharing (optional)
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        # Auto-refresh toggle
        auto_refresh = st.toggle("Auto-refresh", value=True, key="auto_refresh_toggle")
        if auto_refresh:
            st.caption("Page will auto-refresh every 3 seconds")
        else:
            st.caption("Auto-refresh disabled")

def render_winner_screen(winner: str, p1_score: int, p2_score: int) -> None:
    """
    Render the winner announcement screen.
    
    Args:
        winner: "p1", "p2", or "draw"
        p1_score: Player 1 final score
        p2_score: Player 2 final score
    """
    st.markdown("# 🏆 Match Complete!")
    
    # Determine winner display
    if winner == "p1":
        st.success("🎉 **Player 1 Wins!**")
        st.balloons()
    elif winner == "p2":
        st.success("🎉 **Player 2 Wins!**")
        st.balloons()
    else:
        st.info("🤝 **It's a Draw!**")
    
    # Final scores
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Player 1 Score", value=p1_score)
    
    with col2:
        st.markdown(" ")  # Spacing
        st.markdown(" ")  # Spacing
        st.metric(label="Player 2 Score", value=p2_score)
    
    # Play again button
    st.markdown("---")
    if st.button("🔄 Play Again", type="primary", use_container_width=True):
        st.session_state.clear()
        st.experimental_rerun()

if __name__ == "__main__":
    # Test the module
    print("Layout Components Module - Testing interface")
    print("render_header(p1_score, p2_score, match_status): Renders header with metrics")
    print("render_problem_panel(problem_data): Displays problem details")
    print("render_results(results, review_data): Shows test results and AI review")
    print("render_match_info(match_id, player_name): Shows match info in sidebar")
    print("render_winner_screen(winner, p1_score, p2_score): Announces match winner")
