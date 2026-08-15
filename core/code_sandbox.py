"""
core/code_sandbox.py — local code execution against test cases.

Public API
----------
execute_solution(user_code, test_cases) -> ExecutionResult
calculate_score(passed, total, ai_bonus) -> int

NOTE: exec() on untrusted code is NOT safe for production.
For a public deployment, run submissions inside Docker / Firecracker / 
a restricted subprocess with CPU + memory limits.
"""

from __future__ import annotations

import re
import traceback
import logging
from dataclasses import dataclass, field
from typing import Any

from utils.config import (
    MAX_CODE_LENGTH,
    MAX_TEST_SCORE,
    AI_BONUS_MIN,
    AI_BONUS_MAX,
    BLOCKED_SUBSTRINGS,
    BLOCKED_REGEX,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    """Result for a single test case."""
    case_label: str
    input_repr: str
    expected:   str
    actual:     str
    passed:     bool
    error:      str = ""

    @property
    def status_icon(self) -> str:
        if self.error:
            return "❌ Error"
        return "✅ Pass" if self.passed else "❌ Fail"

    def to_row(self) -> dict[str, str]:
        """Convert to a dict row suitable for st.dataframe."""
        return {
            "Test Case": self.case_label,
            "Input":     self.input_repr,
            "Expected":  self.expected,
            "Output":    self.actual if not self.error else self.error,
            "Status":    self.status_icon,
        }


@dataclass
class ExecutionResult:
    """Aggregated result of running all test cases."""
    rows:        list[dict[str, str]] = field(default_factory=list)
    passed:      int = 0
    total:       int = 0
    success:     bool = True   # False if code failed to execute at all

    @classmethod
    def fatal(cls, message: str, total: int = 0) -> "ExecutionResult":
        """Return a result that represents a total execution failure."""
        return cls(
            rows=[{
                "Test Case": "Error",
                "Input":     "",
                "Expected":  "",
                "Output":    message,
                "Status":    "❌ Fatal Error",
            }],
            passed=0,
            total=total,
            success=False,
        )


# ---------------------------------------------------------------------------
# Sanitiser
# ---------------------------------------------------------------------------

def sanitize_code(code: str) -> str:
    """
    Reject obviously dangerous code.

    Raises ValueError with a descriptive message if a blocked pattern is found.
    This is a basic heuristic, NOT a security guarantee.
    """
    if len(code) > MAX_CODE_LENGTH:
        raise ValueError(
            f"Submission exceeds the maximum allowed length "
            f"({len(code):,} > {MAX_CODE_LENGTH:,} characters)."
        )

    for substring in BLOCKED_SUBSTRINGS:
        if substring in code:
            raise ValueError(
                f"Submission contains a disallowed operation: {substring!r}"
            )

    for pattern in BLOCKED_REGEX:
        if re.search(pattern, code):
            raise ValueError(
                f"Submission contains a disallowed operation: {pattern!r}"
            )

    return code


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _find_solution_function(exec_globals: dict) -> Any:
    """
    Return the user-defined callable from exec'd globals.

    Prefers a function literally named `solve`; falls back to the first
    user-defined callable (excludes builtins and dunder names).
    """
    # Prefer explicit "solve" name as documented in the problem spec
    if "solve" in exec_globals and callable(exec_globals["solve"]):
        return exec_globals["solve"]

    candidates = [
        v for k, v in exec_globals.items()
        if callable(v)
        and not k.startswith("__")
        # exclude built-in types / functions that leak into globals
        and getattr(v, "__module__", None) not in (None, "builtins")
    ]

    if not candidates:
        raise ValueError(
            "No callable function found. "
            "Make sure you define a function (e.g. def solve(...):)"
        )

    return candidates[0]


def _call_function(func: Any, input_args: Any) -> Any:
    """Invoke *func* with *input_args*, handling list / dict / scalar inputs."""
    if isinstance(input_args, list):
        return func(*input_args)
    if isinstance(input_args, dict):
        return func(**input_args)
    return func(input_args)


def _outputs_match(actual: Any, expected: Any) -> bool:
    """
    Compare actual vs expected without false failures from type coercion.

    We try direct equality first, then fall back to string comparison
    (e.g. `[1, 2, 3]` vs a JSON array stored as a list).
    """
    if actual == expected:
        return True
    # Try comparing string representations as a last resort
    return str(actual).strip() == str(expected).strip()


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_test_cases(
    user_code: str,
    test_cases: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], int]:
    """
    Execute *user_code* against *test_cases*.

    Returns:
        (rows, passed_count) where `rows` are ready for `st.dataframe`.
    """
    rows:         list[dict[str, str]] = []
    passed_count: int = 0
    exec_globals: dict = {}

    try:
        exec(compile(user_code, "<submission>", "exec"), exec_globals)  # noqa: S102
        func = _find_solution_function(exec_globals)

    except SyntaxError as exc:
        return [TestResult(
            case_label="—", input_repr="", expected="", actual="",
            passed=False, error=f"Syntax error — line {exc.lineno}: {exc.msg}",
        ).to_row()], 0

    except ValueError as exc:
        return [TestResult(
            case_label="—", input_repr="", expected="", actual="",
            passed=False, error=str(exc),
        ).to_row()], 0

    except Exception as exc:
        return [TestResult(
            case_label="—", input_repr="", expected="", actual="",
            passed=False, error=f"Load error: {exc}",
        ).to_row()], 0

    for idx, tc in enumerate(test_cases):
        label     = f"#{idx + 1}"
        inp       = tc.get("input", [])
        expected  = tc.get("expected_output")

        try:
            actual  = _call_function(func, inp)
            is_pass = _outputs_match(actual, expected)
            if is_pass:
                passed_count += 1

            result = TestResult(
                case_label=label,
                input_repr=str(inp),
                expected=str(expected),
                actual=str(actual),
                passed=is_pass,
            )

        except Exception as exc:
            result = TestResult(
                case_label=label,
                input_repr=str(inp),
                expected=str(expected),
                actual="",
                passed=False,
                error=str(exc),
            )

        rows.append(result.to_row())

    return rows, passed_count


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------

def execute_solution(
    user_code: str,
    test_cases: list[dict[str, Any]],
) -> ExecutionResult:
    """
    Full pipeline: sanitise → compile → run → return structured result.
    """
    total = len(test_cases)

    try:
        sanitized = sanitize_code(user_code)
    except ValueError as exc:
        return ExecutionResult.fatal(f"Security block: {exc}", total=total)

    rows, passed = run_test_cases(sanitized, test_cases)
    return ExecutionResult(rows=rows, passed=passed, total=total, success=True)


def calculate_score(passed_count: int, total_test_cases: int, ai_bonus_score: int) -> int:
    """
    Compute the final score.

    Formula: floor(passed/total * MAX_TEST_SCORE) + ai_bonus_score
    Returns 0 if total_test_cases is 0 to avoid division by zero.
    """
    if total_test_cases == 0:
        return 0

    ai_bonus = max(AI_BONUS_MIN, min(AI_BONUS_MAX, ai_bonus_score))
    test_score = int((passed_count / total_test_cases) * MAX_TEST_SCORE)
    return test_score + ai_bonus
