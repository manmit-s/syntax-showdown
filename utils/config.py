"""
Central configuration and constants.

All magic strings, model names, limits, and defaults live here.
Import from this module rather than hardcoding values elsewhere.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Gemini model names
# ---------------------------------------------------------------------------
GEMINI_PROBLEM_MODEL = "gemini-1.5-flash"
GEMINI_REVIEW_MODEL  = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Match / Firestore constants
# ---------------------------------------------------------------------------
MATCHES_COLLECTION   = "matches"
MATCH_ID_PREFIX      = "clash_"
MATCH_ID_HEX_CHARS   = 6

# Valid values — use these instead of bare strings throughout the codebase
class MatchStatus:
    WAITING  = "waiting"
    ACTIVE   = "active"
    FINISHED = "finished"

class PlayerStatus:
    WAITING   = "waiting"
    JOINED    = "joined"
    SUBMITTED = "submitted"

VALID_PLAYERS        = ("p1", "p2")
VALID_MATCH_STATUSES = (MatchStatus.WAITING, MatchStatus.ACTIVE, MatchStatus.FINISHED)
VALID_DIFFICULTIES   = ("easy", "medium", "hard")

# ---------------------------------------------------------------------------
# Sandbox limits
# ---------------------------------------------------------------------------
MAX_CODE_LENGTH        = 10_000   # characters
NUM_TEST_CASES         = 3

# Dangerous patterns blocked by the sandbox sanitiser
BLOCKED_PATTERNS: tuple[str, ...] = (
    "import os",        "from os import",
    "import sys",       "from sys import",
    "import subprocess","from subprocess import",
    "import socket",    "from socket import",
    "__import__(",      "compile(",
    "open(",            "file(",
    "input(",           "raw_input(",
    # double-check eval/exec with word boundaries so e.g. "evaluate" is fine
    "\beval\b",         "\bexec\b",
)

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
MAX_TEST_SCORE       = 100          # points awarded for passing all test cases
AI_BONUS_MIN         = 0
AI_BONUS_MAX         = 10
AI_BONUS_DEFAULT     = 5            # fallback when AI review fails

# ---------------------------------------------------------------------------
# Polling / UI
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECS   = 3
DEFAULT_DIFFICULTY   = "medium"
