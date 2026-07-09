"""
prompts.py
----------
All prompt engineering lives here, separate from UI/app logic, so the
five required reusable templates (and the extra study-tool prompts)
stay easy to audit, reuse, and swap the topic into.

Techniques used throughout:
- Role prompting        -> PERSONA / SYSTEM_PROMPT anchor every call
- Structured prompting  -> explicit output format instructions
- Few-shot prompting    -> a worked example inside the quiz-evaluation prompt
- Chain-of-thought      -> the model is asked to reason step by step
                           internally, but told to only output the final,
                           clean answer (reasoning is never exposed to the
                           learner)

CHANGE LOG (interactive quiz update):
- prompt_quiz() now asks Gemini for strict JSON instead of free text, so
  the quiz can be rendered as clickable options in the UI and graded
  programmatically after the learner submits.
- Added parse_quiz_json() + grade_quiz() helpers used by app.py.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# AI Buddy Persona (deliverable #2)
# ---------------------------------------------------------------------------
PERSONA_DESCRIPTION = """\
Nova is a patient, encouraging AI study buddy built for beginners who feel
intimidated by new subjects. Nova never talks down to the learner and never
uses jargon without immediately explaining it in plain words. Nova is warm
and upbeat but stays focused on the learner's actual question rather than
padding answers with filler. When a learner gets something wrong, Nova
treats it as a normal part of learning, corrects gently, and explains the
'why' behind the correct answer instead of just stating it. Nova's goal is
always to build the learner's confidence and independence, not dependence
on the AI.
"""

SYSTEM_PROMPT = """\
You are Nova, a patient and encouraging AI learning buddy for beginners.

Rules you always follow:
1. Use simple, plain language. Avoid jargon; if a technical term is
   unavoidable, define it in the same sentence.
2. Keep answers focused and concise — clear beats exhaustive.
3. Be warm and encouraging, especially when the learner makes a mistake.
   Never mock or scold; explain the reasoning behind the correct answer.
4. Reason through the problem step by step internally before answering,
   but only show the learner your final, clean answer — never expose your
   internal chain of thought or working notes.
5. When asked for facts, be accurate. If you are not confident about
   something, say so plainly instead of guessing.
6. Stay on topic: gently redirect the learner back to the subject if the
   conversation drifts somewhere unrelated to learning.
"""


def _wrap(user_instruction: str) -> str:
    """Attach the system prompt / persona to every outbound request."""
    return f"{SYSTEM_PROMPT}\n\nTask:\n{user_instruction}"


# ---------------------------------------------------------------------------
# The five required reusable prompt templates (deliverable #3)
# Each is topic-agnostic: swap {topic} and it still works for anything.
# ---------------------------------------------------------------------------

def prompt_explain(topic: str) -> str:
    """Template 1 — Explain the topic in simple language."""
    return _wrap(
        f"Explain '{topic}' in simple language for a complete beginner. "
        "Use a short analogy if it helps. Keep it to 4-6 sentences, "
        "then add one bolded 'Key takeaway' line at the end."
    )


def prompt_example(topic: str) -> str:
    """Template 2 — Give one real-life example."""
    return _wrap(
        f"Give one clear, relatable real-life example of '{topic}' that a "
        "beginner would recognize from everyday life. Explain in 2-3 "
        "sentences why the example illustrates the concept."
    )


def prompt_quiz(topic: str, num_questions: int = 5) -> str:
    """Template 3 — Generate a multiple-choice quiz.

    Returns STRICT JSON (no markdown fences, no prose before/after) so the
    app can render each question as clickable radio options and grade the
    learner's picks after they submit, instead of just dumping raw text.
    """
    return _wrap(
        f"Create {num_questions} multiple-choice questions on '{topic}' for "
        "a beginner.\n\n"
        "Respond with ONLY a valid JSON array — no markdown code fences, "
        "no explanation before or after, nothing but the JSON itself. "
        "Each array element must be an object with exactly these keys:\n"
        '  "question"    -> string, the question text\n'
        '  "options"     -> object with exactly keys "A", "B", "C", "D", '
        "each mapped to a short answer-option string\n"
        '  "correct"     -> string, one of "A", "B", "C", "D" — the '
        "correct option's letter\n"
        '  "explanation" -> string, one short sentence on why that answer '
        "is correct\n\n"
        "Example of the exact shape required (structure only, do not reuse "
        "this content):\n"
        '[{"question": "...", "options": {"A": "...", "B": "...", '
        '"C": "...", "D": "..."}, "correct": "B", "explanation": "..."}]'
    )


def prompt_evaluate(topic: str, question: str, learner_answer: str) -> str:
    """Template 4 — Evaluate/give feedback on a learner's answer.

    Includes a short few-shot example so the model matches the tone and
    format we want before it evaluates the real answer.
    """
    example = (
        "Example of the style to follow:\n"
        "Question: What does CPU stand for?\n"
        "Learner's answer: Central Process Unit\n"
        "Feedback: Close! It's actually 'Central Processing Unit' — you "
        "had the right idea, just a small wording slip. Processing is the "
        "key word because the CPU is constantly *processing* instructions.\n"
    )
    return _wrap(
        f"{example}\n"
        f"Now evaluate this learner's answer about '{topic}'.\n"
        f"Question: {question}\n"
        f"Learner's answer: {learner_answer}\n\n"
        "Say clearly whether it's correct, partially correct, or incorrect, "
        "then explain why in 2-3 encouraging sentences. If it's wrong, "
        "give the correct answer too."
    )


def prompt_full_session(topic: str) -> str:
    """Template 5 — Full learning session (explain + example + quiz)."""
    return _wrap(
        f"Run a complete beginner learning session on '{topic}':\n"
        "1) Explain the concept simply (4-6 sentences).\n"
        "2) Give one real-life example.\n"
        "3) Ask 3 short quiz questions (no answers yet — wait for the "
        "learner to attempt them first).\n"
        "Use clear section headers for each of the 3 parts."
    )


def prompt_ask_anything(topic_context: str, question: str) -> str:
    return _wrap(
        f"The learner is currently studying '{topic_context}'. "
        f"They ask: \"{question}\". Answer helpfully and simply, relating "
        "back to the topic where relevant."
    )


# ---------------------------------------------------------------------------
# Quiz JSON parsing + grading helpers (used by the interactive Quiz Zone)
# ---------------------------------------------------------------------------

def parse_quiz_json(raw_text: str) -> Optional[List[Dict[str, Any]]]:
    """Parse Gemini's quiz response into a list of question dicts.

    Tolerant of stray ```json fences or leading/trailing prose, since
    models occasionally add them despite instructions. Returns None if the
    text can't be turned into a valid quiz structure.
    """
    if not raw_text:
        return None

    text = raw_text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present.
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # If there's stray prose around the array, grab the outermost [ ... ].
    if not text.startswith("["):
        bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
        if bracket_match:
            text = bracket_match.group(0)

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(data, list) or not data:
        return None

    required_keys = {"question", "options", "correct", "explanation"}
    valid_questions: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or not required_keys.issubset(item.keys()):
            continue
        options = item.get("options")
        if not isinstance(options, dict) or not options:
            continue
        if item.get("correct") not in options:
            continue
        valid_questions.append(item)

    return valid_questions or None


def grade_quiz(
    questions: List[Dict[str, Any]], learner_answers: Dict[int, str]
) -> Dict[str, Any]:
    """Compare learner's selected letters against correct answers.

    `learner_answers` maps question index -> selected option letter
    (e.g. {0: "B", 1: "A", ...}).

    Returns a dict with the overall score and a per-question breakdown
    that the UI can render as ✅ / ❌ with the correct answer + explanation.
    """
    breakdown = []
    correct_count = 0
    for i, q in enumerate(questions):
        picked = learner_answers.get(i)
        is_correct = picked == q["correct"]
        if is_correct:
            correct_count += 1
        breakdown.append(
            {
                "question": q["question"],
                "options": q["options"],
                "picked": picked,
                "correct_letter": q["correct"],
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            }
        )
    return {
        "correct_count": correct_count,
        "total": len(questions),
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# Extra study-tool prompts (beyond the 5 required templates)
# ---------------------------------------------------------------------------

def prompt_flashcards(topic: str, n: int = 8) -> str:
    return _wrap(
        f"Create {n} flashcards on '{topic}' for a beginner. Format each "
        "as 'Q: ...' on one line and 'A: ...' on the next, separated by a "
        "blank line. Keep answers to one short sentence."
    )


def prompt_summary(topic: str) -> str:
    return _wrap(
        f"Write a concise study summary of '{topic}' in 5-7 bullet points, "
        "beginner-friendly, covering only the most essential ideas."
    )


def prompt_revision_notes(topic: str) -> str:
    return _wrap(
        f"Write structured revision notes on '{topic}' with 3-4 short "
        "headed sections, each with 2-3 bullet points. Beginner level."
    )


def prompt_formula_sheet(topic: str) -> str:
    return _wrap(
        f"If '{topic}' has any standard formulas, laws, or equations, list "
        "them with a one-line explanation of each variable. If the topic "
        "has no formulas, instead list its 3-4 core rules or principles "
        "in the same style."
    )


def prompt_mnemonics(topic: str) -> str:
    return _wrap(
        f"Create 1-2 simple mnemonics or memory tricks to help a beginner "
        f"remember the key facts about '{topic}'. Explain each briefly."
    )


def prompt_mindmap(topic: str) -> str:
    return _wrap(
        f"Create a text-based mind map of '{topic}' using nested "
        "bullet indentation: one central idea, 3-5 main branches, and "
        "1-2 sub-points under each branch."
    )


def prompt_interview_questions(topic: str, n: int = 6) -> str:
    return _wrap(
        f"Write {n} interview-style questions on '{topic}', ranging from "
        "beginner to intermediate difficulty, each followed by a short "
        "model answer."
    )


def prompt_coding_questions(topic: str, n: int = 4) -> str:
    return _wrap(
        f"Write {n} short coding practice questions related to '{topic}' "
        "(skip this activity gracefully if the topic isn't code-related — "
        "say so instead of forcing irrelevant questions). Include a brief "
        "hint for each, but not the full solution."
    )


def prompt_related_topics(topic: str) -> str:
    return _wrap(
        f"List 5 topics closely related to '{topic}' that a learner "
        "should explore next, each with a one-sentence reason why."
    )


def prompt_further_reading(topic: str) -> str:
    return _wrap(
        f"Suggest 4 types of further-reading resources for '{topic}' "
        "(e.g. kinds of books, reputable sites, courses) without inventing "
        "fake specific titles or URLs. Describe what to look for instead."
    )


def prompt_common_mistakes(topic: str) -> str:
    return _wrap(
        f"List 4 common mistakes or misconceptions beginners have about "
        f"'{topic}', each with a one-sentence correction."
    )


def prompt_learning_tips(topic: str) -> str:
    return _wrap(
        f"Give 4 practical study tips specifically suited to learning "
        f"'{topic}' as a beginner."
    )


def prompt_daily_challenge(topic: str) -> str:
    return _wrap(
        f"Set one small, concrete practice challenge related to '{topic}' "
        "that a beginner could complete in under 15 minutes today."
    )


ACTIVITY_PROMPT_MAP = {
    "Explain Concept": lambda topic, **kw: prompt_explain(topic),
    "Real-Life Example": lambda topic, **kw: prompt_example(topic),
    "Generate Quiz": lambda topic, **kw: prompt_quiz(topic),
    "Ask Anything": lambda topic, **kw: prompt_ask_anything(topic, kw.get("question", topic)),
    "Flashcards": lambda topic, **kw: prompt_flashcards(topic),
    "Summary Generator": lambda topic, **kw: prompt_summary(topic),
    "Revision Notes": lambda topic, **kw: prompt_revision_notes(topic),
    "Formula Sheet": lambda topic, **kw: prompt_formula_sheet(topic),
    "Mnemonics": lambda topic, **kw: prompt_mnemonics(topic),
    "Mind Map (Text)": lambda topic, **kw: prompt_mindmap(topic),
    "Interview Questions": lambda topic, **kw: prompt_interview_questions(topic),
    "Coding Questions": lambda topic, **kw: prompt_coding_questions(topic),
    "Related Topics": lambda topic, **kw: prompt_related_topics(topic),
    "Further Reading": lambda topic, **kw: prompt_further_reading(topic),
    "Common Mistakes": lambda topic, **kw: prompt_common_mistakes(topic),
    "Learning Tips": lambda topic, **kw: prompt_learning_tips(topic),
    "Daily Challenge": lambda topic, **kw: prompt_daily_challenge(topic),
}