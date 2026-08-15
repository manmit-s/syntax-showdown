"""
core/db_client.py — Firebase Firestore integration.

Public API
----------
initialize_firebase()                   one-time SDK setup (idempotent)
create_match(problem_data) -> str       create a new match, return match_id
get_match_state(match_id) -> dict|None  read a match document
update_player_state(match_id, player, updates)
update_match_status(match_id, status)
join_match_as_p2(match_id) -> bool
resolve_player_id(match_id) -> str      determine which slot a new visitor gets
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

from utils.config import (
    MATCHES_COLLECTION,
    MATCH_ID_PREFIX,
    MATCH_ID_HEX_CHARS,
    MatchStatus,
    PlayerStatus,
    VALID_PLAYERS,
    VALID_MATCH_STATUSES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_initialized() -> bool:
    return bool(firebase_admin._apps)


def _get_db() -> firestore.Client:
    """Return the Firestore client, initializing the SDK if needed."""
    if not _is_initialized():
        initialize_firebase()
    return firestore.client()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()



# ---------------------------------------------------------------------------
# Firestore sanitiser
# ---------------------------------------------------------------------------

def _to_firestore_safe(value):
    """
    Recursively convert a value to a Firestore-safe type.

    Firestore supports: str, int, float, bool, None, list, dict.
    It rejects: tuples, sets, custom objects, bytes with wrong encoding.

    Gemini sometimes returns:
      - None as expected_output
      - Tuples inside input lists
      - Integers where strings are expected (or vice-versa)

    We normalise everything so Firestore never sees an unsupported type.
    """
    if value is None:
        return ""          # Firestore allows None but it causes issues downstream
    if isinstance(value, bool):
        return value       # bool before int — bool is subclass of int
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_to_firestore_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_firestore_safe(v) for k, v in value.items()}
    # Anything else (e.g. a custom object) — convert to string
    return str(value)


def _sanitise_problem_data(problem_data: dict) -> dict:
    """
    Return a deep-cleaned copy of problem_data safe for Firestore storage.
    Ensures all test case inputs and expected_outputs are serialisable.
    """
    safe = _to_firestore_safe(problem_data)

    # Extra pass: make sure every test case has the right shape
    for tc in safe.get("test_cases", []):
        if not isinstance(tc.get("input"), list):
            tc["input"] = [tc["input"]] if tc.get("input") is not None else []
        if "expected_output" not in tc:
            tc["expected_output"] = ""

    return safe

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK using credentials from Streamlit secrets.
    Idempotent — safe to call on every rerun.
    """
    if _is_initialized():
        return

    raw: dict | None = st.secrets.get("firebase_credentials")
    if not raw:
        raise EnvironmentError(
            "firebase_credentials not found in Streamlit secrets. "
            "Copy .streamlit/secrets.toml.example and fill in your Firebase credentials."
        )

    cred = credentials.Certificate(dict(raw))
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialised.")


def generate_match_id() -> str:
    """Return a unique match ID like `clash_a3f9c1`."""
    return f"{MATCH_ID_PREFIX}{uuid.uuid4().hex[:MATCH_ID_HEX_CHARS]}"


def create_match(problem_data: dict) -> str:
    """
    Create a new match document in Firestore.

    Args:
        problem_data: Validated problem dict from `ai_engine.generate_problem`.

    Returns:
        The newly created match_id string.
    """
    db       = _get_db()
    match_id = generate_match_id()

    doc: dict = {
        "created_at": _utc_now(),
        "status": MatchStatus.WAITING,
        "problem_data": _sanitise_problem_data(problem_data),
        "players": {
            "p1": {"code": "", "score": 0, "status": PlayerStatus.JOINED},
            "p2": {"code": "", "score": 0, "status": PlayerStatus.WAITING},
        },
    }

    db.collection(MATCHES_COLLECTION).document(match_id).set(doc)
    logger.info("Match created: %s", match_id)
    return match_id


def get_match_state(match_id: str) -> Optional[dict]:
    """
    Fetch the current state of a match.

    Returns:
        Match dict (with `id` key injected) or `None` if not found.
    """
    db  = _get_db()
    doc = db.collection(MATCHES_COLLECTION).document(match_id).get()

    if not doc.exists:
        logger.warning("Match not found: %s", match_id)
        return None

    data       = doc.to_dict()
    data["id"] = match_id
    return data


def update_player_state(match_id: str, player: str, updates: dict) -> None:
    """
    Atomically update player-specific fields.

    Args:
        match_id: Firestore document ID.
        player:   `"p1"` or `"p2"`.
        updates:  Field-value pairs, e.g. `{"score": 80, "status": "submitted"}`.
    """
    if player not in VALID_PLAYERS:
        raise ValueError(f"player must be one of {VALID_PLAYERS}, got {player!r}")

    db         = _get_db()
    flat_patch = {f"players.{player}.{k}": v for k, v in updates.items()}
    db.collection(MATCHES_COLLECTION).document(match_id).update(flat_patch)
    logger.info("Updated %s in match %s: %s", player, match_id, updates)


def update_match_status(match_id: str, status: str) -> None:
    """
    Update the top-level `status` field of a match.

    Args:
        status: One of `MatchStatus.WAITING / ACTIVE / FINISHED`.
    """
    if status not in VALID_MATCH_STATUSES:
        raise ValueError(f"status must be one of {VALID_MATCH_STATUSES}, got {status!r}")

    db = _get_db()
    db.collection(MATCHES_COLLECTION).document(match_id).update({"status": status})
    logger.info("Match %s status -> %s", match_id, status)


def join_match_as_p2(match_id: str) -> bool:
    """
    Atomically claim the p2 slot and activate the match.

    Returns:
        `True` if p2 slot was claimed, `False` if already taken or match missing.
    """
    db      = _get_db()
    doc_ref = db.collection(MATCHES_COLLECTION).document(match_id)

    @firestore.transactional
    def _txn(transaction: firestore.Transaction) -> bool:
        snapshot = doc_ref.get(transaction=transaction)
        if not snapshot.exists:
            return False

        p2_status = snapshot.get("players.p2.status")
        if p2_status != PlayerStatus.WAITING:
            logger.info("Match %s: p2 slot already taken.", match_id)
            return False

        transaction.update(doc_ref, {
            "players.p2.status": PlayerStatus.JOINED,
            "status": MatchStatus.ACTIVE,
        })
        return True

    txn    = db.transaction()
    result = _txn(txn)
    if result:
        logger.info("Player 2 joined match %s.", match_id)
    return result


def resolve_player_id(match_id: str, session_player_id: Optional[str]) -> str:
    """
    Determine which player slot the current visitor occupies.

    This is a *pure data-layer* function — it does NOT write to session_state.
    The caller (app.py) is responsible for persisting the returned value.

    Logic:
    - If the caller already has a valid player_id (e.g. from session state), honour it.
    - If p2 slot is still `waiting`, claim it and return `"p2"`.
    - Otherwise, default to `"p1"` (e.g. creator refreshed the page).

    Returns:
        `"p1"` or `"p2"`.
    """
    if session_player_id in VALID_PLAYERS:
        return session_player_id

    match_data = get_match_state(match_id)
    if not match_data:
        raise ValueError(f"Match not found: {match_id}")

    p2_status = match_data.get("players", {}).get("p2", {}).get("status")
    if p2_status == PlayerStatus.WAITING:
        success = join_match_as_p2(match_id)
        if success:
            return "p2"

    return "p1"
