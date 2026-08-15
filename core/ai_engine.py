"""
core/ai_engine.py — Google Gemini integration (google-genai SDK).

Public API
----------
initialize_gemini()            one-time client setup (idempotent, process-level)
generate_problem(difficulty)   returns a validated problem dict
review_code(title, user_code)  returns a validated review dict
"""

from __future__ import annotations

import json
import re
import time
import logging

import streamlit as st
from google import genai

from utils.config import (
    GEMINI_PROBLEM_MODEL,
    GEMINI_REVIEW_MODEL,
    NUM_TEST_CASES,
    AI_BONUS_MIN,
    AI_BONUS_MAX,
    AI_BONUS_DEFAULT,
    VALID_DIFFICULTIES,
)

import warnings
warnings.filterwarnings('ignore', message='.*AFC.*')

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level client — set once by initialize_gemini(), reused everywhere.
# Using a module-level variable (not session_state) because the Client object
# is a plain Python object with no Streamlit dependency; it is safe to share
# across reruns and sessions within the same process.
# ---------------------------------------------------------------------------
_client: genai.Client | None = None


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PROBLEM_PROMPT = """\
You are a competitive programming puzzle generator.

Generate a random {difficulty}-level coding problem.

Output exactly as a JSON object using this format:

{{
  "title": "String",
  "description": "String",
  "constraints": ["String"],
  "starter_code": "def solve(input_var):\\n    pass",
  "test_cases": [
    {{
      "input": [args],
      "expected_output": value
    }}
  ]
}}

Generate exactly {num_test_cases} test cases.
Do not include Markdown formatting.
Do not include triple backticks or json fences.
Return only the JSON object.\
"""

_REVIEW_PROMPT = """\
You are a strict competitive programming code reviewer.

Review the following Python solution for the problem titled:
"{title}"

Evaluate the code for:
1. Time complexity using Big-O notation.
2. Space complexity using Big-O notation.
3. Edge-case handling.
4. General correctness concerns.
5. Code quality and style.

Provide a witty, slightly roasting review of the code style.

Return exactly this JSON format:

{{
  "time_complexity": "O(...)",
  "space_complexity": "O(...)",
  "roast_review": "String",
  "ai_bonus_score": 0
}}

The ai_bonus_score must be an integer from 0 to 10 based on efficiency and code quality.
Do not include Markdown formatting.
Do not include triple backticks or json fences.
Return only the JSON object.

Problem title:
{title}

Submitted code:
{user_code}\
"""

_PROBLEM_REQUIRED_KEYS = {"title", "description", "constraints", "starter_code", "test_cases"}
_REVIEW_REQUIRED_KEYS  = {"time_complexity", "space_complexity", "roast_review", "ai_bonus_score"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> genai.Client:
    """Return the module-level client, raising clearly if not initialised."""
    if _client is None:
        raise RuntimeError(
            "Gemini client not initialised. "
            "Call initialize_gemini() before generating content."
        )
    return _client


def _clean_json_response(text: str) -> str:
    """Strip markdown fences and extract the outermost JSON object."""
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]

    return text


def _call_with_retry(model_name: str, prompt: str, max_retries: int = 3) -> str:
    """
    Call the Gemini API and return response text.
    Retries up to max_retries times with exponential back-off.
    """
    client    = _get_client()
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt
            logger.warning(
                "Gemini call failed (attempt %d/%d): %s — retrying in %ds",
                attempt, max_retries, exc, wait,
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Gemini call failed after {max_retries} attempts"
    ) from last_exc


def _parse_and_validate(raw_text: str, required_keys: set[str]) -> dict:
    """Clean, parse, and validate a Gemini JSON response."""
    cleaned = _clean_json_response(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failure. Raw text:\n%s", raw_text[:500])
        raise ValueError("Gemini returned invalid JSON") from exc

    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Gemini response missing required keys: {missing}")

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_gemini() -> None:
    """
    Create the Gemini Client using the API key from Streamlit secrets.

    Idempotent — if the client already exists this is a no-op.
    Stores the client at module level (not in session_state) so it is
    shared across all sessions in the same process without needing
    st.secrets on every rerun.
    """
    global _client
    if _client is not None:
        return

    api_key: str | None = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not found in Streamlit secrets. "
            "Add it to .streamlit/secrets.toml or the Streamlit Cloud secrets panel."
        )

    _client = genai.Client(api_key=api_key)
    logger.info("Gemini Client initialised (google-genai SDK).")


def generate_problem(difficulty: str) -> dict:
    """
    Generate a competitive programming problem via Gemini.

    Args:
        difficulty: One of "easy", "medium", "hard".

    Returns:
        Validated problem dict: title, description, constraints,
        starter_code, test_cases.
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"difficulty must be one of {VALID_DIFFICULTIES}, got {difficulty!r}"
        )

    prompt   = _PROBLEM_PROMPT.format(
        difficulty=difficulty,
        num_test_cases=NUM_TEST_CASES,
    )
    raw_text = _call_with_retry(GEMINI_PROBLEM_MODEL, prompt)
    problem  = _parse_and_validate(raw_text, _PROBLEM_REQUIRED_KEYS)

    actual = len(problem.get("test_cases", []))
    if actual != NUM_TEST_CASES:
        logger.warning("Expected %d test cases, got %d", NUM_TEST_CASES, actual)

    return problem


def review_code(title: str, user_code: str) -> dict:
    """
    Review submitted code using Gemini.

    Args:
        title:     Problem title.
        user_code: Submitted Python code.

    Returns:
        Validated review dict: time_complexity, space_complexity,
        roast_review, ai_bonus_score.
    """
    if not title:
        raise ValueError("title must not be empty")
    if not user_code or not user_code.strip():
        raise ValueError("user_code must not be empty")

    prompt   = _REVIEW_PROMPT.format(title=title, user_code=user_code)
    raw_text = _call_with_retry(GEMINI_REVIEW_MODEL, prompt)
    review   = _parse_and_validate(raw_text, _REVIEW_REQUIRED_KEYS)

    score = review.get("ai_bonus_score")
    if not isinstance(score, int) or not (AI_BONUS_MIN <= score <= AI_BONUS_MAX):
        logger.warning(
            "ai_bonus_score %r out of range; defaulting to %d", score, AI_BONUS_DEFAULT
        )
        review["ai_bonus_score"] = AI_BONUS_DEFAULT

    return review
