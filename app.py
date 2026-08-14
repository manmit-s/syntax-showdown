"""
1v1 Code Clash Arena - Main Application

A real-time 1v1 competitive programming platform built with Streamlit,
Google Gemini, and Firebase Firestore.
"""

import streamlit as st
import time

# Import core modules
from core import ai_engine, db_client, code_sandbox
from utils import state_manager

# Import UI components
from components import layout, editors, forms


# Page configuration
st.set_page_config(
    page_title="1v1 Code Clash Arena",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_lobby():
    """Render the lobby screen where users can create matches."""
    st.markdown("# ⚔️ 1v1 Code Clash Arena")
    st.markdown("### Real-time Competitive Programming")
    
    # Welcome message
    st.markdown("""
    Welcome to the **1v1 Code Clash Arena**! Challenge your friends in real-time 
    coding battles where AI generates unique problems and judges your solutions.
    
    **How it works:**
    1. Create a match and select difficulty
    2. Share the link with your opponent
    3. Both solve the same AI-generated problem
    4. AI evaluates and roasts your code
    5. Highest score wins! 🏆
    """)
    
    st.markdown("---")
    
    # Render match creation form
    form_result = forms.render_match_creation_form()
    
    if form_result:
        difficulty = form_result["difficulty"]
        
        # Show loading spinner
        with st.spinner("🤖 AI is generating a unique problem..."):
            try:
                # Initialize Gemini
                ai_engine.initialize_gemini()
                
                # Generate problem
                problem_data = ai_engine.generate_problem(difficulty)
                st.success(f"✅ Problem generated: {problem_data.get('title', 'Unknown')}")
                
                # Create match in Firestore
                db_client.initialize_firebase()
                match_id = db_client.create_match(problem_data)
                
                st.success(f"🎉 Match created! Match ID: {match_id}")
                
                # Update query params and rerun
                st.query_params["match_id"] = match_id
                st.query_params["player"] = "p1"
                
                # Update session state
                state_manager.update_player_state("p1", match_id)
                
                # Rerun to enter the match
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to create match: {str(e)}")
                st.info("Make sure you have configured your API keys in .streamlit/secrets.toml")


def render_waiting_screen(match_id: str, match_data: dict):
    """Render the waiting screen when match is waiting for opponent."""
    st.markdown("# ⏳ Waiting for Opponent")
    
    # Match info
    forms.render_match_url_display(match_id)
    
    st.markdown("---")
    
    # Poll status
    forms.render_poll_status(
        match_data.get("updated_at", "Unknown"),
        match_data.get("status", "waiting")
    )
    
    # Instructions
    st.markdown("""
    ### What's happening?
    
    Your match is waiting for Player 2 to join. Share the match link above 
    with your opponent!
    
    ### While you wait...
    
    Take a look at the problem that was generated for you:
    """)
    
    # Show problem preview
    problem_data = match_data.get("problem_data", {})
    with st.expander("👀 Preview Problem", expanded=True):
        st.markdown(f"**{problem_data.get('title', 'Loading...')}**")
        st.markdown(problem_data.get("description", "")[:500] + "...")
    
    # Auto-refresh polling
    time.sleep(3)
    st.rerun()


def render_arena(match_id: str, match_data: dict, player_id: str):
    """Render the main arena where players solve the problem."""
    # Get match data
    problem_data = match_data.get("problem_data", {})
    players = match_data.get("players", {})
    
    # Get player and opponent data
    player_data = players.get(player_id, {})
    opponent_id = "p2" if player_id == "p1" else "p1"
    opponent_data = players.get(opponent_id, {})
    
    p1_score = players.get("p1", {}).get("score", 0)
    p2_score = players.get("p2", {}).get("score", 0)
    match_status = match_data.get("status", "active")
    
    # Render header with scores
    layout.render_header(p1_score, p2_score, match_status)
    
    # Render sidebar with match info
    player_name = f"Player {player_id.replace('p', '')}"
    layout.render_match_info(match_id, player_name)
    
    # Check if both players have submitted
    p1_submitted = players.get("p1", {}).get("status") == "submitted"
    p2_submitted = players.get("p2", {}).get("status") == "submitted"
    
    if p1_submitted and p2_submitted and match_status != "finished":
        # Both submitted - end the match
        db_client.update_match_status(match_id, "finished")
        st.rerun()
    
    # Create two columns: problem and code editor
    problem_col, editor_col = st.columns([1, 1])
    
    with problem_col:
        st.markdown("### 🎯 The Challenge")
        layout.render_problem_panel(problem_data)
    
    with editor_col:
        # Check if already submitted
        if player_data.get("status") == "submitted":
            st.markdown("### ✅ Already Submitted!")
            
            # Show results
            results = st.session_state.get("last_results", [])
            review_data = st.session_state.get("last_ai_review", {})
            
            layout.render_results(results, review_data)
            
            # Show submitted code in read-only mode
            submitted_code = player_data.get("code", "")
            if submitted_code:
                st.markdown("### 📤 Your Submission")
                st.code(submitted_code, language="python")
            
            st.info("⏳ Waiting for opponent to submit...")
            
            # Auto-refresh
            time.sleep(3)
            st.rerun()
        else:
            # Show submission form
            starter_code = problem_data.get("starter_code", "")
            user_code, was_submitted = forms.render_submission_form(starter_code)
            
            if was_submitted:
                # Process submission
                process_submission(match_id, player_id, user_code, problem_data)
    
    # Show both players' status
    st.markdown("---")
    st.markdown("### 👥 Player Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        p1_status = players.get("p1", {}).get("status", "unknown")
        p1_status_emoji = "✅" if p1_status == "submitted" else "⏳"
        st.metric(
            label=f"{p1_status_emoji} Player 1",
            value=players.get("p1", {}).get("score", 0),
            delta="Submitted" if p1_status == "submitted" else "Waiting"
        )
    
    with col2:
        p2_status = players.get("p2", {}).get("status", "unknown")
        p2_status_emoji = "✅" if p2_status == "submitted" else "⏳"
        st.metric(
            label=f"{p2_status_emoji} Player 2",
            value=players.get("p2", {}).get("score", 0),
            delta="Submitted" if p2_status == "submitted" else "Waiting"
        )
    
    # Auto-refresh if match is still active
    if match_status == "active" and (not p1_submitted or not p2_submitted):
        if state_manager.should_refresh():
            time.sleep(1)
            st.rerun()


def process_submission(match_id: str, player_id: str, user_code: str, problem_data: dict):
    """Process a code submission."""
    try:
        with st.spinner("🔄 Running tests and generating AI review..."):
            # Get test cases
            test_cases = problem_data.get("test_cases", [])
            
            # Run code against test cases
            execution_result = code_sandbox.execute_solution(user_code, test_cases)
            
            if not execution_result["success"]:
                # Show error
                st.error("❌ Code execution failed!")
                results = execution_result.get("results", [])
                for result in results:
                    st.markdown(f"**{result.get('Status')}:** {result.get('Output', '')}")
                return
            
            results = execution_result["results"]
            passed_count = execution_result["passed_count"]
            total_tests = execution_result["total_tests"]
            
            # Get AI review
            try:
                ai_review = ai_engine.review_code(
                    problem_data.get("title", "Untitled"),
                    user_code
                )
            except Exception as e:
                st.warning(f"⚠️ AI review failed: {str(e)}. Using default review.")
                ai_review = {
                    "time_complexity": "N/A",
                    "space_complexity": "N/A",
                    "roast_review": "AI review unavailable. Your code probably works though!",
                    "ai_bonus_score": 5
                }
            
            # Calculate score
            ai_bonus = ai_review.get("ai_bonus_score", 0)
            score = code_sandbox.calculate_score(passed_count, total_tests, ai_bonus)
            
            # Update session state
            state_manager.update_submission_state(user_code, results, score, ai_review)
            
            # Update Firestore
            db_client.update_player_state(
                match_id,
                player_id,
                {
                    "code": user_code,
                    "score": score,
                    "status": "submitted"
                }
            )
            
            st.success(f"✅ Submitted! Score: {score}")
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Failed to process submission: {str(e)}")


def render_results_screen(match_id: str, match_data: dict, player_id: str):
    """Render the final results screen."""
    players = match_data.get("players", {})
    p1_score = players.get("p1", {}).get("score", 0)
    p2_score = players.get("p2", {}).get("score", 0)
    
    # Determine winner
    if p1_score > p2_score:
        winner = "p1"
    elif p2_score > p1_score:
        winner = "p2"
    else:
        winner = "draw"
    
    # Render winner screen
    layout.render_winner_screen(winner, p1_score, p2_score)
    
    # Show both players' submissions
    st.markdown("---")
    st.markdown("## 📋 Final Submissions")
    
    p1_code = players.get("p1", {}).get("code", "")
    p2_code = players.get("p2", {}).get("code", "")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎮 Player 1")
        if p1_code:
            st.code(p1_code, language="python")
        else:
            st.info("No code submitted")
    
    with col2:
        st.markdown("### 🎮 Player 2")
        if p2_code:
            st.code(p2_code, language="python")
        else:
            st.info("No code submitted")
    
    # New match button
    st.markdown("---")
    if st.button("🔄 Create New Match", type="primary", use_container_width=True):
        # Clear session state and redirect to lobby
        state_manager.clear_match_state()
        st.query_params.clear()
        st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    state_manager.init_session_state()
    
    # Get match ID from query params
    match_id = st.query_params.get("match_id")
    
    if match_id is None:
        # No match ID - show lobby
        render_lobby()
    else:
        # Match ID exists - load match data
        try:
            db_client.initialize_firebase()
            match_data = db_client.get_match_state(match_id)
            
            if match_data is None:
                st.error(f"❌ Match not found: {match_id}")
                st.button("← Back to Lobby", on_click=lambda: st.query_params.clear())
                return
            
            # Determine player role
            player_id = st.query_params.get("player")
            
            if player_id is None:
                # Try to get from session state
                player_id = st.session_state.get("player_id")
            
            if player_id is None:
                # Determine player role by checking available slot
                players = match_data.get("players", {})
                p2_status = players.get("p2", {}).get("status")
                
                if p2_status == "waiting":
                    # Player 2 slot is available
                    player_id = "p2"
                    st.query_params["player"] = "p2"
                    db_client.join_match_as_p2(match_id)
                elif players.get("p1", {}).get("status") == "joined":
                    # Could be p1 returning or p2
                    player_id = "p1"
                    st.query_params["player"] = "p1"
                else:
                    # Both joined - determine who we are
                    player_id = "p1"  # Default fallback
                
                state_manager.update_player_state(player_id, match_id)
                st.rerun()
            
            # Route based on match status
            match_status = match_data.get("status", "waiting")
            
            if match_status == "waiting":
                render_waiting_screen(match_id, match_data)
            elif match_status == "active":
                render_arena(match_id, match_data, player_id)
            elif match_status == "finished":
                render_results_screen(match_id, match_data, player_id)
            else:
                st.error(f"❌ Unknown match status: {match_status}")
                
        except Exception as e:
            st.error(f"❌ Error loading match: {str(e)}")
            st.button("← Back to Lobby", on_click=lambda: st.query_params.clear())


if __name__ == "__main__":
    main()
