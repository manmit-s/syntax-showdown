"""
components/layout.py — reusable Streamlit UI building blocks.

All functions are pure renderers: they receive data as arguments and
call st.* — they do NOT read from session_state or call any core modules.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.config import MatchStatus


# ---------------------------------------------------------------------------
# Scoreboard header
# ---------------------------------------------------------------------------

def render_header(p1_score: int, p2_score: int, match_status: str) -> None:
    """Render the 3-column score dashboard."""
    col_p1, col_status, col_p2 = st.columns(3)

    with col_p1:
        delta = (p1_score - p2_score) if p1_score != p2_score else None
        st.metric("🎮 Player 1", p1_score, delta=delta)

    with col_status:
        _STATUS_EMOJI = {
            MatchStatus.WAITING:  "⏳",
            MatchStatus.ACTIVE:   "⚔️",
            MatchStatus.FINISHED: "🏆",
        }
        emoji  = _STATUS_EMOJI.get(match_status, "❓")
        st.metric("Match Status", f"{emoji} {match_status.title()}")

    with col_p2:
        delta = (p2_score - p1_score) if p2_score != p1_score else None
        st.metric("🎮 Player 2", p2_score, delta=delta)

    st.divider()


# ---------------------------------------------------------------------------
# Problem panel
# ---------------------------------------------------------------------------

def render_problem_panel(problem_data: dict) -> None:
    """Render the problem statement, constraints and example test cases."""
    st.markdown(f"## 🎯 {problem_data.get('title', 'Untitled Problem')}")
    st.markdown(problem_data.get("description", "*No description provided.*"))

    with st.expander("📋 Constraints & Examples", expanded=True):
        constraints = problem_data.get("constraints", [])
        if constraints:
            st.markdown("**Constraints**")
            for c in constraints:
                st.markdown(f"- {c}")

        test_cases = problem_data.get("test_cases", [])
        if test_cases:
            st.markdown("**Example Test Cases**")
            rows = [
                {
                    "Case":            f"#{i + 1}",
                    "Input":           str(tc.get("input")),
                    "Expected Output": str(tc.get("expected_output")),
                }
                for i, tc in enumerate(test_cases)
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    starter = problem_data.get("starter_code", "")
    if starter:
        st.markdown("**Starter Code**")
        st.code(starter, language="python")


# ---------------------------------------------------------------------------
# Results panel
# ---------------------------------------------------------------------------

def render_results(results: list[dict], review_data: dict) -> None:
    """Render test-case results table and AI code review."""
    # --- Test results ---
    st.markdown("### 📊 Test Results")
    if results:
        df = pd.DataFrame(results)

        def _status_style(val: str) -> str:
            if "✅" in val:
                return "color: #22c55e; font-weight: bold"
            if "❌" in val:
                return "color: #ef4444; font-weight: bold"
            return ""

        st.dataframe(
            df.style.map(_status_style, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )

        passed = sum(1 for r in results if "✅" in str(r.get("Status", "")))
        total  = len(results)
        pct    = passed / total * 100 if total else 0
        st.caption(f"Passed {passed}/{total} &nbsp;·&nbsp; {pct:.0f}%")
    else:
        st.info("No test results yet.")

    # --- AI review ---
    st.markdown("### 🤖 AI Code Review")
    if not review_data:
        st.info("AI review not available.")
        return

    st.info(f"💬 {review_data.get('roast_review', 'No review.')}")

    col_tc, col_sc, col_bonus = st.columns(3)
    col_tc.metric("⏱️ Time Complexity",  review_data.get("time_complexity",  "N/A"))
    col_sc.metric("💾 Space Complexity", review_data.get("space_complexity", "N/A"))

    bonus = review_data.get("ai_bonus_score", 0)
    col_bonus.metric("⭐ AI Bonus", f"{bonus} / 10")
    st.progress(bonus / 10)


# ---------------------------------------------------------------------------
# Sidebar match info
# ---------------------------------------------------------------------------

def render_match_info(match_id: str, player_name: str, share_url: str) -> None:
    """
    Render the sidebar panel with match metadata and share link.

    Args:
        match_id:    Firestore document ID.
        player_name: Human-readable name for the current player.
        share_url:   Full URL the opponent should open.
    """
    with st.sidebar:
        st.markdown("## 📍 Match Info")
        st.markdown(f"**You are:** {player_name}")
        st.markdown(f"**Match ID:** {match_id}")

        st.markdown("---")
        st.markdown("### 🔗 Invite Your Opponent")
        st.code(share_url, language="text")
        st.caption("Copy the URL above and send it to your opponent.")

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        auto = st.toggle("Auto-refresh (every 3 s)", value=True, key="auto_refresh_toggle")
        st.session_state["auto_refresh"] = auto


# ---------------------------------------------------------------------------
# Winner / finish screen
# ---------------------------------------------------------------------------

def render_winner_screen(
    winner: str,
    p1_score: int,
    p2_score: int,
    show_balloons: bool = False,
) -> None:
    """
    Announce the match result.

    Args:
        winner:        `"p1"`, `"p2"`, or `"draw"`.
        p1_score:      Final score for Player 1.
        p2_score:      Final score for Player 2.
        show_balloons: Pass `True` only on the first render (use the
                       `state_manager.should_show_balloons()` guard).
    """
    st.markdown("# 🏆 Match Complete!")

    _WINNER_MESSAGES = {
        "p1":   ("🎉 Player 1 Wins!", "success"),
        "p2":   ("🎉 Player 2 Wins!", "success"),
        "draw": ("🤝 It's a Draw!",   "info"),
    }
    message, kind = _WINNER_MESSAGES.get(winner, ("Match finished.", "info"))

    if show_balloons:
        st.balloons()

    getattr(st, kind)(f"**{message}**")

    col1, col2 = st.columns(2)
    col1.metric("Player 1 Score", p1_score)
    col2.metric("Player 2 Score", p2_score)
