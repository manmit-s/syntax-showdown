"""
utils/state_manager.py — Streamlit session-state helpers.

Centralises all reads and writes to st.session_state so the rest of the
codebase never has to know the exact key names.
"""

from __future__ import annotations

import time
import urllib.parse
import logging

import streamlit as st

from utils.config import POLL_INTERVAL_SECS, DEFAULT_DIFFICULTY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key registry — one place to rename a key if needed
# ---------------------------------------------------------------------------
_K_PLAYER_ID      = "player_id"
_K_MATCH_ID       = "match_id"
_K_DIFFICULTY     = "difficulty"
_K_SUBMITTED      = "submitted"
_K_SUBMITTED_CODE = "submitted_code"
_K_CURRENT_CODE   = "current_code"
_K_LAST_RESULTS   = "last_results"
_K_LAST_SCORE     = "last_score"
_K_LAST_REVIEW    = "last_ai_review"
_K_AUTO_REFRESH   = "auto_refresh"
_K_LAST_POLL      = "last_poll_time"
_K_POLL_INTERVAL  = "poll_interval"
_K_BALLOONS_SHOWN = "balloons_shown"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    """
    Set default values for all session-state keys.
    Safe to call on every Streamlit rerun — setdefault is a no-op if the
    key already exists.
    """
    defaults = {
        _K_PLAYER_ID:      None,
        _K_MATCH_ID:       None,
        _K_DIFFICULTY:     DEFAULT_DIFFICULTY,
        _K_SUBMITTED:      False,
        _K_SUBMITTED_CODE: "",
        _K_CURRENT_CODE:   "",
        _K_LAST_RESULTS:   [],
        _K_LAST_SCORE:     0,
        _K_LAST_REVIEW:    {},
        _K_AUTO_REFRESH:   True,
        _K_LAST_POLL:      0.0,
        _K_POLL_INTERVAL:  POLL_INTERVAL_SECS,
        _K_BALLOONS_SHOWN: False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ---------------------------------------------------------------------------
# Player / match identity
# ---------------------------------------------------------------------------

def update_player_state(player_id: str, match_id: str) -> None:
    """Persist which player role and match this session belongs to."""
    st.session_state[_K_PLAYER_ID] = player_id
    st.session_state[_K_MATCH_ID]  = match_id


def get_player_id() -> str | None:
    return st.session_state.get(_K_PLAYER_ID)


def get_match_id() -> str | None:
    return st.session_state.get(_K_MATCH_ID)


def get_player_display_name() -> str:
    pid = get_player_id()
    return {"p1": "Player 1", "p2": "Player 2"}.get(pid, "Unknown")


def get_opponent_display_name() -> str:
    pid = get_player_id()
    return {"p1": "Player 2", "p2": "Player 1"}.get(pid, "Unknown")


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------

def update_submission_state(
    code: str,
    results: list,
    score: int,
    ai_review: dict,
) -> None:
    """Persist everything that results from a successful code submission."""
    st.session_state[_K_SUBMITTED]      = True
    st.session_state[_K_SUBMITTED_CODE] = code
    st.session_state[_K_CURRENT_CODE]   = code
    st.session_state[_K_LAST_RESULTS]   = results
    st.session_state[_K_LAST_SCORE]     = score
    st.session_state[_K_LAST_REVIEW]    = ai_review


def is_submitted() -> bool:
    return bool(st.session_state.get(_K_SUBMITTED, False))


def get_last_results() -> list:
    return st.session_state.get(_K_LAST_RESULTS, [])


def get_last_score() -> int:
    return st.session_state.get(_K_LAST_SCORE, 0)


def get_last_review() -> dict:
    return st.session_state.get(_K_LAST_REVIEW, {})


def get_submitted_code() -> str:
    return st.session_state.get(_K_SUBMITTED_CODE, "")


def get_current_code(fallback: str = "") -> str:
    return st.session_state.get(_K_CURRENT_CODE) or fallback


# ---------------------------------------------------------------------------
# Match lifecycle
# ---------------------------------------------------------------------------

def clear_match_state() -> None:
    """Reset all match-specific keys while preserving user preferences."""
    st.session_state[_K_PLAYER_ID]      = None
    st.session_state[_K_MATCH_ID]       = None
    st.session_state[_K_SUBMITTED]      = False
    st.session_state[_K_SUBMITTED_CODE] = ""
    st.session_state[_K_CURRENT_CODE]   = ""
    st.session_state[_K_LAST_RESULTS]   = []
    st.session_state[_K_LAST_SCORE]     = 0
    st.session_state[_K_LAST_REVIEW]    = {}
    st.session_state[_K_BALLOONS_SHOWN] = False


# ---------------------------------------------------------------------------
# Auto-refresh / polling
# ---------------------------------------------------------------------------

def should_refresh() -> bool:
    """
    Return True (and update the timestamp) if enough time has elapsed since
    the last poll.  Respects the auto_refresh toggle in session state.
    """
    if not st.session_state.get(_K_AUTO_REFRESH, True):
        return False

    now      = time.monotonic()
    last     = st.session_state.get(_K_LAST_POLL, 0.0)
    interval = st.session_state.get(_K_POLL_INTERVAL, POLL_INTERVAL_SECS)

    if now - last >= interval:
        st.session_state[_K_LAST_POLL] = now
        return True

    return False


# ---------------------------------------------------------------------------
# Winner balloon guard
# ---------------------------------------------------------------------------

def should_show_balloons() -> bool:
    """Return True the *first* time the finished screen is rendered."""
    if not st.session_state.get(_K_BALLOONS_SHOWN, False):
        st.session_state[_K_BALLOONS_SHOWN] = True
        return True
    return False


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def get_shareable_url(match_id: str) -> str:
    """
    Build a shareable URL for a match using the current page's host.

    Streamlit exposes the browser URL via st.context (>=1.37) or falls back
    to a relative path that works on Streamlit Community Cloud.
    """
    try:
        # st.context.url is available in Streamlit >= 1.37
        base = str(st.context.url).split("?")[0]
    except AttributeError:
        base = "/"

    params = urllib.parse.urlencode({"match_id": match_id})
    return f"{base}?{params}"
