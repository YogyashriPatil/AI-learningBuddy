"""
config.py
---------
Central configuration for the AI Learning Buddy app.
Holds constants, page metadata, theme palettes, and the list of
activities shown in the sidebar. Keeping these in one place makes the
app easy to re-skin or extend without touching app logic.
"""

from __future__ import annotations
from dataclasses import dataclass

APP_NAME = "AI Learning Buddy"
APP_ICON = "🎓"
APP_TAGLINE = "Your personal, patient AI tutor — for any topic, any time."

GEMINI_MODEL_NAME = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Activities available in the sidebar. Each maps to a prompt-builder in
# prompts.py. Grouped so the sidebar can render them as labeled sections.
# ---------------------------------------------------------------------------
CORE_ACTIVITIES = [
    "Explain Concept",
    "Real-Life Example",
    "Generate Quiz",
    "Evaluate My Answer",
    "Ask Anything",
]

STUDY_TOOL_ACTIVITIES = [
    "Flashcards",
    "Summary Generator",
    "Revision Notes",
    "Formula Sheet",
    "Mnemonics",
    "Mind Map (Text)",
]

CAREER_PREP_ACTIVITIES = [
    "Interview Questions",
    "Coding Questions",
]

EXPLORE_ACTIVITIES = [
    "Related Topics",
    "Further Reading",
    "Common Mistakes",
    "Learning Tips",
    "Daily Challenge",
]

ALL_ACTIVITIES = (
    CORE_ACTIVITIES + STUDY_TOOL_ACTIVITIES + CAREER_PREP_ACTIVITIES + EXPLORE_ACTIVITIES
)

# ---------------------------------------------------------------------------
# Theme palettes (used to build the injected CSS custom properties)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Theme:
    name: str
    bg_gradient: str
    card_bg: str
    text_color: str
    subtext_color: str
    accent: str
    accent_soft: str
    border: str


LIGHT_THEME = Theme(
    name="light",
    bg_gradient="linear-gradient(135deg, #eef2ff 0%, #f5f3ff 45%, #fdf4ff 100%)",
    card_bg="rgba(255, 255, 255, 0.65)",
    text_color="#1e1b2e",
    subtext_color="#5b5470",
    accent="#7c3aed",
    accent_soft="rgba(124, 58, 237, 0.12)",
    border="rgba(124, 58, 237, 0.18)",
)

DARK_THEME = Theme(
    name="dark",
    bg_gradient="linear-gradient(135deg, #0f0c1d 0%, #17122b 45%, #1c1330 100%)",
    card_bg="rgba(255, 255, 255, 0.06)",
    text_color="#f2eefc",
    subtext_color="#b8b0cf",
    accent="#a78bfa",
    accent_soft="rgba(167, 139, 250, 0.16)",
    border="rgba(167, 139, 250, 0.25)",
)

QUIZ_SIZE = 5  # number of MCQs generated per quiz, per assignment spec