"""
components/editors.py — code-editor widgets.

These are pure rendering helpers — no session_state writes, no core calls.
The caller passes data in; return values come back out.
"""

from __future__ import annotations

import streamlit as st

_DEFAULT_HEIGHT = 360


def render_code_editor(
    starter_code: str,
    current_code: str,
    key: str = "code_editor",
) -> str:
    """
    Render a plain text-area code editor.

    Args:
        starter_code: The AI-generated boilerplate (shown when the user hasn't
                      typed anything yet).
        current_code: Whatever the user has typed so far (from session state).
        key:          Unique Streamlit widget key.

    Returns:
        The current contents of the editor.
    """
    value = current_code if current_code.strip() else starter_code
    return st.text_area(
        label="📝 Your Solution",
        value=value,
        height=_DEFAULT_HEIGHT,
        key=key,
        help="Write your Python solution here. Define a function that accepts the input and returns the output.",
    )


def render_code_readonly(code: str, label: str = "") -> None:
    """Display code in a read-only block."""
    if label:
        st.markdown(f"**{label}**")
    if code.strip():
        st.code(code, language="python")
    else:
        st.caption("*(empty)*")


def render_code_stats(code: str) -> None:
    """
    Display lightweight code statistics as Streamlit metrics.
    Intended for the sidebar or a narrow column.
    """
    lines    = code.splitlines()
    nonempty = [l for l in lines if l.strip()]
    has_fn   = "def " in code

    st.markdown("#### 📊 Stats")
    st.metric("Lines", len(nonempty))
    st.metric("Chars", len(code))
    if has_fn:
        st.success("✅ Function defined")
    else:
        st.warning("⚠️ No function found")
