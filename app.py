"""
app.py — Syntax Showdown entry point.

Responsibilities:
  • Page config and one-time SDK initialisation (guarded so it runs once).
  • Read match_id from query params and route to the correct screen.
  • Own all session-state reads/writes via state_manager.
  • Orchestrate calls between core modules and UI components.

Core modules (ai_engine, db_client, code_sandbox) are kept free of UI concerns.
UI components (layout, forms, editors) are kept free of business-logic concerns.
"""

from __future__ import annotations

import logging
import time

import streamlit as st

from core import ai_engine, db_client, code_sandbox
from utils import state_manager
from utils.config import MatchStatus
from components import layout, forms

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config — must be the FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Syntax Showdown",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)




# ---------------------------------------------------------------------------
# Screen renderers
# ---------------------------------------------------------------------------

def _render_lobby() -> None:
    st.markdown("# ⚔️ Syntax Showdown")
    st.markdown("### Real-time competitive programming, powered by AI")
    st.markdown("""
**How it works**
1. Create a match and pick a difficulty.
2. Share the generated link with your opponent.
3. Both of you solve the same AI-generated problem.
4. Gemini reviews your code and awards a bonus score.
5. Highest total wins. 🏆
""")
    st.divider()

    form_result = forms.render_match_creation_form()
    if not form_result:
        return

    difficulty = form_result["difficulty"]

    with st.spinner("🤖 Generating your problem…"):
        try:
            problem_data = ai_engine.generate_problem(difficulty)
        except Exception as exc:
            st.error(f"Could not generate a problem: {exc}")
            st.info("Check that GEMINI_API_KEY is set in your secrets.")
            return

    with st.spinner("💾 Creating match in Firestore…"):
        try:
            match_id = db_client.create_match(problem_data)
        except Exception as exc:
            st.error(f"Could not create the match: {exc}")
            st.info("Check your firebase_credentials in secrets.")
            return

    # Persist player role and navigate
    state_manager.update_player_state("p1", match_id)
    st.query_params["match_id"] = match_id
    st.query_params["player"]   = "p1"
    st.rerun()


def _render_waiting(match_id: str, match_data: dict) -> None:
    st.markdown("# ⏳ Waiting for Opponent")

    share_url = state_manager.get_shareable_url(match_id)
    forms.render_share_url(share_url)
    forms.render_match_status_badge(MatchStatus.WAITING)

    problem_data = match_data.get("problem_data", {})
    with st.expander("👀 Preview the Problem", expanded=True):
        st.markdown(f"**{problem_data.get('title', '…')}**")
        preview = problem_data.get("description", "")[:400]
        st.markdown(preview + ("…" if len(problem_data.get("description","")) > 400 else ""))

    # Polling — use st.rerun after a short sleep so we don't burn the thread.
    # The sleep is tiny here; the 3-second effective cadence is enforced by
    # should_refresh() checking elapsed wall-clock time.
    if state_manager.should_refresh():
        time.sleep(1)
        st.rerun()


def _process_submission(
    match_id: str,
    player_id: str,
    user_code: str,
    problem_data: dict,
) -> None:
    """Run tests, call AI review, persist everything, then rerun."""
    with st.spinner("⚡ Running tests and generating AI review…"):

        # 1. Execute code
        test_cases       = problem_data.get("test_cases", [])
        execution_result = code_sandbox.execute_solution(user_code, test_cases)

        # 2. AI review (best-effort — we never fail the submission because of it)
        try:
            ai_review = ai_engine.review_code(
                problem_data.get("title", "Untitled"),
                user_code,
            )
        except Exception as exc:
            logger.warning("AI review failed: %s", exc)
            from utils.config import AI_BONUS_DEFAULT
            ai_review = {
                "time_complexity":  "N/A",
                "space_complexity": "N/A",
                "roast_review":     "AI review temporarily unavailable. Still a solid run though!",
                "ai_bonus_score":   AI_BONUS_DEFAULT,
            }

        # 3. Calculate score
        score = code_sandbox.calculate_score(
            execution_result.passed,
            execution_result.total,
            ai_review.get("ai_bonus_score", 0),
        )

        # 4. Persist to session state and Firestore
        state_manager.update_submission_state(
            user_code, execution_result.rows, score, ai_review
        )
        db_client.update_player_state(
            match_id, player_id,
            {"code": user_code, "score": score, "status": "submitted"},
        )

    st.rerun()


def _render_arena(match_id: str, match_data: dict, player_id: str) -> None:
    players   = match_data.get("players", {})
    p1        = players.get("p1", {})
    p2        = players.get("p2", {})
    my_data   = players.get(player_id, {})
    opp_id    = "p2" if player_id == "p1" else "p1"
    opp_data  = players.get(opp_id, {})

    # If both submitted, close the match (only p1 does this to avoid a race)
    both_done = (p1.get("status") == "submitted" and p2.get("status") == "submitted")
    if both_done and match_data.get("status") != MatchStatus.FINISHED:
        if player_id == "p1":
            db_client.update_match_status(match_id, MatchStatus.FINISHED)
        st.rerun()

    # --- Header ---
    layout.render_header(
        p1.get("score", 0),
        p2.get("score", 0),
        match_data.get("status", MatchStatus.ACTIVE),
    )

    # --- Sidebar ---
    share_url = state_manager.get_shareable_url(match_id)
    layout.render_match_info(match_id, state_manager.get_player_display_name(), share_url)

    # --- Main split ---
    problem_data  = match_data.get("problem_data", {})
    prob_col, ed_col = st.columns(2)

    with prob_col:
        layout.render_problem_panel(problem_data)

    with ed_col:
        already_submitted = my_data.get("status") == "submitted"

        if already_submitted:
            st.success("✅ Submission received!")
            layout.render_results(
                state_manager.get_last_results(),
                state_manager.get_last_review(),
            )
            st.markdown("#### Your Submitted Code")
            from components.editors import render_code_readonly
            render_code_readonly(state_manager.get_submitted_code())

        else:
            starter_code = problem_data.get("starter_code", "")
            current_code = state_manager.get_current_code(fallback=starter_code)

            user_code, was_submitted = forms.render_submission_form(
                starter_code=starter_code,
                current_code=current_code,
            )

            # Persist editor content between reruns
            if user_code != current_code:
                st.session_state["current_code"] = user_code

            if was_submitted:
                _process_submission(match_id, player_id, user_code, problem_data)

    # --- Player status bar ---
    st.divider()
    st.markdown("### 👥 Player Status")
    sc1, sc2 = st.columns(2)

    def _player_metric(col, name, data):
        submitted = data.get("status") == "submitted"
        icon      = "✅" if submitted else "⏳"
        col.metric(f"{icon} {name}", data.get("score", 0),
                   delta="Submitted" if submitted else "Coding…")

    _player_metric(sc1, "Player 1", p1)
    _player_metric(sc2, "Player 2", p2)

    # Polling
    if not both_done and state_manager.should_refresh():
        time.sleep(0.5)
        st.rerun()


def _render_results_screen(match_id: str, match_data: dict) -> None:
    players  = match_data.get("players", {})
    p1_score = players.get("p1", {}).get("score", 0)
    p2_score = players.get("p2", {}).get("score", 0)

    winner = "p1" if p1_score > p2_score else ("p2" if p2_score > p1_score else "draw")

    layout.render_winner_screen(
        winner, p1_score, p2_score,
        show_balloons=state_manager.should_show_balloons(),
    )

    st.divider()
    st.markdown("## 📋 Final Submissions")

    p1_code = players.get("p1", {}).get("code", "")
    p2_code = players.get("p2", {}).get("code", "")

    from components.editors import render_code_readonly
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🎮 Player 1")
        render_code_readonly(p1_code or "*(no submission)*")
    with c2:
        st.markdown("### 🎮 Player 2")
        render_code_readonly(p2_code or "*(no submission)*")

    st.divider()
    if st.button("🔄 Create New Match", type="primary", use_container_width=True):
        state_manager.clear_match_state()
        st.query_params.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

def main() -> None:
    # Session defaults must come first — everything below may read session state.
    state_manager.init_session_state()

    # Initialise Firebase (guarded by firebase_admin._apps — runs once per process)
    try:
        db_client.initialize_firebase()
    except Exception as exc:
        st.error(f"⚠️ Firebase init failed: {exc}")
        st.info(
            "Check the [firebase_credentials] block in .streamlit/secrets.toml. "
            "Make sure the private_key is on one line with literal \\n characters."
        )
        st.stop()

    # Initialise Gemini (guarded by module-level _client — runs once per process)
    try:
        ai_engine.initialize_gemini()
    except Exception as exc:
        st.error(f"⚠️ Gemini init failed: {exc}")
        st.info(
            "Check that GEMINI_API_KEY is set correctly in .streamlit/secrets.toml. "
            "Get a key at https://aistudio.google.com/app/apikey"
        )
        st.stop()

    match_id = st.query_params.get("match_id")

    # --- Lobby ---
    if match_id is None:
        _render_lobby()
        return

    # --- Load match ---
    try:
        match_data = db_client.get_match_state(match_id)
    except Exception as exc:
        st.error(f"Could not load match: {exc}")
        if st.button("← Back to Lobby"):
            st.query_params.clear()
            st.rerun()
        return

    if match_data is None:
        st.error(f"Match {match_id} not found.")
        if st.button("← Back to Lobby"):
            st.query_params.clear()
            st.rerun()
        return

    # --- Resolve player identity (pure logic, no UI side-effects) ---
    stored_player = state_manager.get_player_id() or st.query_params.get("player")
    try:
        player_id = db_client.resolve_player_id(match_id, stored_player)
    except Exception as exc:
        st.error(str(exc))
        return

    # Persist if it changed (e.g. new visitor claiming p2)
    if player_id != state_manager.get_player_id():
        state_manager.update_player_state(player_id, match_id)
        st.query_params["player"] = player_id
        st.rerun()

    # --- Route ---
    status = match_data.get("status", MatchStatus.WAITING)

    if status == MatchStatus.WAITING:
        _render_waiting(match_id, match_data)
    elif status == MatchStatus.ACTIVE:
        _render_arena(match_id, match_data, player_id)
    elif status == MatchStatus.FINISHED:
        _render_results_screen(match_id, match_data)
    else:
        st.error(f"Unknown match status: {status!r}")


if __name__ == "__main__":
    main()
