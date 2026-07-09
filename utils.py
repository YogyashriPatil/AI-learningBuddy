"""
utils.py
--------
Reusable helper functions kept out of app.py so the main file stays
readable: Gemini API access, session-state initialization, and small
formatting/download helpers.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import streamlit as st

from config import GEMINI_MODEL_NAME


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------
def get_api_key() -> str | None:
    """Resolve the Gemini API key from st.secrets first, then env vars.

    The key is NEVER hardcoded in source. Order of precedence:
    1. st.secrets["GEMINI_API_KEY"]        (Streamlit Cloud / local secrets.toml)
    2. os.environ["GEMINI_API_KEY"]        (Colab / local shell export)
    """
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY")


@st.cache_resource(show_spinner=False)
def _load_model(api_key: str):
    """Create (and cache) the Gemini model client for this session."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL_NAME)


def call_gemini(prompt: str) -> str:
    """Send a prompt to Gemini and return plain text, with error handling.

    Any failure (missing key, network issue, safety block, etc.) is caught
    and turned into a friendly message instead of crashing the app.
    """
    api_key = get_api_key()
    if not api_key:
        return (
            "⚠️ No Gemini API key found. Add one to `.streamlit/secrets.toml` "
            "as `GEMINI_API_KEY = \"your-key\"`, or set the `GEMINI_API_KEY` "
            "environment variable, then rerun the app."
        )
    try:
        model = _load_model(api_key)
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if not text:
            return "⚠️ Gemini returned an empty response. Please try again."
        return text
    except Exception as exc:  # noqa: BLE001 - surface any API error safely
        return f"⚠️ Something went wrong talking to Gemini: {exc}"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_session_state() -> None:
    """Set up every piece of session state the app relies on, once."""
    defaults: dict[str, Any] = {
        "theme": "light",
        "chat_history": [],          # list of {role, content, activity, ts}
        "bookmarks": [],             # list of {topic, activity, content}
        "quiz_score": {"correct": 0, "attempted": 0},
        "badges": set(),
        "current_topic": "",
        "last_quiz_raw": "",
        "xp": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_to_history(activity: str, topic: str, content: str, role: str = "assistant") -> None:
    st.session_state.chat_history.append(
        {
            "role": role,
            "activity": activity,
            "topic": topic,
            "content": content,
            "ts": datetime.now().strftime("%H:%M:%S"),
        }
    )


def award_xp(amount: int = 10) -> None:
    st.session_state.xp += amount
    _check_badges()


def _check_badges() -> None:
    milestones = {
        50: "🌱 Getting Started",
        150: "📘 Curious Learner",
        300: "🔥 On a Roll",
        600: "🏆 Learning Champion",
    }
    for threshold, badge in milestones.items():
        if st.session_state.xp >= threshold:
            st.session_state.badges.add(badge)


def reset_app() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


# ---------------------------------------------------------------------------
# Formatting / download helpers
# ---------------------------------------------------------------------------
def as_download_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def build_transcript(topic: str) -> str:
    """Render the full chat history for this topic as plain text."""
    lines = [f"AI Learning Buddy — Session Transcript", f"Topic: {topic}", "-" * 40]
    for turn in st.session_state.chat_history:
        who = "You" if turn["role"] == "user" else "Nova"
        lines.append(f"[{turn['ts']}] {who} ({turn['activity']}):\n{turn['content']}\n")
    return "\n".join(lines)