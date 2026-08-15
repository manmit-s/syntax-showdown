"""
components/forms.py — form widgets.

Pure rendering helpers: receive data as arguments, return user input.
No session_state reads/writes, no core module calls.
"""

from __future__ import annotations

import streamlit as st

from components.editors import render_code_editor, render_code_stats
from utils.config import VALID_DIFFICULTIES, DEFAULT_DIFFICULTY


# ---------------------------------------------------------------------------
# Lobby
# ---------------------------------------------------------------------------

_DIFFICULTY_DESCRIPTIONS = {
    "easy":   "Simple algorithms, basic data structures",
    "medium": "Moderate complexity, common interview questions",
    "hard":   "Complex algorithms, optimisation challenges",
}


def render_match_creation_form() -> dict | None:
    """
    Render the lobby form.

    Returns:
        `{"difficulty": str}` on submission, `None` otherwise.
    """
    st.markdown("## 🎮 Create a New Match")

    with st.form("match_creation_form", border=True):
        difficulty = st.selectbox(
            "Difficulty",
            options=list(VALID_DIFFICULTIES),
            index=list(VALID_DIFFICULTIES).index(DEFAULT_DIFFICULTY),
            help="Choose how hard the generated problem should be.",
        )
        st.caption(f"💡 {_DIFFICULTY_DESCRIPTIONS.get(difficulty, '')}")
        st.divider()

        if st.form_submit_button("🚀 Create Match", type="primary", use_container_width=True):
            return {"difficulty": difficulty}

    return None


# ---------------------------------------------------------------------------
# Arena
# ---------------------------------------------------------------------------

def render_submission_form(
    starter_code: str,
    current_code: str,
    key: str = "submission_form",
) -> tuple[str, bool]:
    """
    Render the code-submission form.

    Args:
        starter_code: AI-generated boilerplate.
        current_code: What the user has typed so far (from session state).
        key:          Unique Streamlit form key.

    Returns:
        `(user_code, was_submitted)`
    """
    col_editor, col_stats = st.columns([5, 1])

    # We need the editor value even before form submission, so render it
    # outside the form (stats panel reads it in real-time).
    with col_editor:
        with st.form(key, border=True):
            user_code = render_code_editor(
                starter_code=starter_code,
                current_code=current_code,
                key=f"{key}_editor",
            )

            st.caption(
                "💡 **Scoring:** test pass rate (0–100 pts) + AI bonus (0–10 pts)"
            )
            st.divider()
            submitted = st.form_submit_button(
                "⚡ Run & Evaluate",
                type="primary",
                use_container_width=True,
            )

    with col_stats:
        render_code_stats(current_code or starter_code)

    if submitted:
        stripped = user_code.strip()
        if not stripped:
            st.error("Please write some code before submitting.")
            return user_code, False
        if "def " not in user_code:
            st.warning("Your submission doesn't define a function yet.")
            return user_code, False
        return user_code, True

    return user_code, False


# ---------------------------------------------------------------------------
# Share URL display
# ---------------------------------------------------------------------------

def render_share_url(share_url: str) -> None:
    """Display the shareable match URL in a copyable code block."""
    st.markdown("### 🔗 Invite Your Opponent")
    st.code(share_url, language="text")
    st.caption("Copy this URL and send it to your opponent.")


# ---------------------------------------------------------------------------
# Status indicator
# ---------------------------------------------------------------------------

_STATUS_CONFIG: dict[str, tuple[str, str, str]] = {
    "waiting":  ("⏳", "Waiting for opponent…", "#f97316"),
    "active":   ("⚔️", "Match in progress!",    "#22c55e"),
    "finished": ("🏆", "Match finished!",        "#a855f7"),
}


def render_match_status_badge(match_status: str) -> None:
    """Render a styled status badge."""
    emoji, msg, colour = _STATUS_CONFIG.get(match_status, ("❓", "Unknown", "#6b7280"))
    st.markdown(
        f"""
        <div style="padding:12px;border-radius:8px;background:{colour}22;
                    border:1px solid {colour};text-align:center;margin:8px 0;">
            <span style="font-size:28px;">{emoji}</span><br>
            <span style="color:{colour};font-weight:600;">{msg}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
