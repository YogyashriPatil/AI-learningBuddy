"""
app.py
------
AI Learning Buddy — main Streamlit application.

Run locally:
    streamlit run app.py

Requires a Gemini API key set via `.streamlit/secrets.toml` or the
`GEMINI_API_KEY` environment variable. See README.md for full deployment
instructions (Streamlit Cloud / local / Google Colab + ngrok).

CHANGE LOG (interactive quiz update):
- Quiz Zone (Tab 3) now generates a structured quiz (see prompts.prompt_quiz
  + prompts.parse_quiz_json) and renders each question with clickable
  options. The learner picks an answer for every question, then presses
  "Submit Quiz" — only THEN does the app reveal what was correct/incorrect,
  the right answer, and a short explanation, plus an overall score.
- A few new session_state keys are used: quiz_questions, quiz_answers,
  quiz_submitted, quiz_topic_name, last_quiz_correct_count. They're set up
  defensively with setdefault() below so this works even if utils.py's
  init_session_state() hasn't been updated to include them.
"""

from __future__ import annotations

import streamlit as st

from config import (
    APP_NAME,
    APP_ICON,
    APP_TAGLINE,
    CORE_ACTIVITIES,
    STUDY_TOOL_ACTIVITIES,
    CAREER_PREP_ACTIVITIES,
    EXPLORE_ACTIVITIES,
    LIGHT_THEME,
    DARK_THEME,
)
from prompts import (
    PERSONA_DESCRIPTION,
    ACTIVITY_PROMPT_MAP,
    prompt_evaluate,
    prompt_full_session,
    prompt_quiz,
    parse_quiz_json,
    grade_quiz,
)
from utils import (
    init_session_state,
    call_gemini,
    add_to_history,
    award_xp,
    reset_app,
    build_transcript,
    as_download_bytes,
)

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="wide")

init_session_state()

# Defensive defaults for the interactive quiz feature — safe no-ops if
# utils.init_session_state() already sets these.
st.session_state.setdefault("quiz_questions", None)   # parsed list[dict] or None
st.session_state.setdefault("quiz_answers", {})        # {question_index: "A"/"B"/"C"/"D"}
st.session_state.setdefault("quiz_submitted", False)
st.session_state.setdefault("quiz_topic_name", "")
st.session_state.setdefault("last_quiz_correct_count", 0)


def inject_css() -> None:
    theme = DARK_THEME if st.session_state.theme == "dark" else LIGHT_THEME
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
    vars_css = f"""
    <style>
    :root {{
        --lb-bg-gradient: {theme.bg_gradient};
        --lb-card-bg: {theme.card_bg};
        --lb-text: {theme.text_color};
        --lb-subtext: {theme.subtext_color};
        --lb-accent: {theme.accent};
        --lb-accent-soft: {theme.accent_soft};
        --lb-border: {theme.border};
    }}
    </style>
    """
    st.markdown(vars_css, unsafe_allow_html=True)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


inject_css()

# ---------------------------------------------------------------------------
# Sidebar — navigation, topic, theme, session controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## {APP_ICON} {APP_NAME}")
    st.caption(APP_TAGLINE)

    st.session_state.current_topic = st.text_input(
        "📚 Topic", value=st.session_state.current_topic, placeholder="e.g. Photosynthesis"
    )

    st.markdown("#### Activity")
    activity_group = st.radio(
        "Category",
        ["Core", "Study Tools", "Career Prep", "Explore"],
        horizontal=True,
        label_visibility="collapsed",
    )
    group_map = {
        "Core": CORE_ACTIVITIES,
        "Study Tools": STUDY_TOOL_ACTIVITIES,
        "Career Prep": CAREER_PREP_ACTIVITIES,
        "Explore": EXPLORE_ACTIVITIES,
    }
    activity = st.selectbox("Choose Activity", group_map[activity_group])

    st.divider()
    dark_mode = st.toggle("🌙 Dark Mode", value=(st.session_state.theme == "dark"))
    st.session_state.theme = "dark" if dark_mode else "light"

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with col_b:
        if st.button("♻️ Reset App", use_container_width=True):
            reset_app()
            st.rerun()

    st.divider()
    st.markdown("#### 📊 Progress")
    st.metric("XP", st.session_state.xp)
    score = st.session_state.quiz_score
    accuracy = (
        f"{round(100 * score['correct'] / score['attempted'])}%"
        if score["attempted"]
        else "—"
    )
    st.metric("Quiz Accuracy", accuracy)
    if st.session_state.badges:
        st.markdown("**Badges:**")
        st.markdown(
            "".join(f"<span class='lb-badge'>{b}</span>" for b in st.session_state.badges),
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="lb-hero">
        <h1>{APP_ICON} {APP_NAME}</h1>
        <p>{APP_TAGLINE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs(["🏠 Dashboard", "💬 Learning Studio", "📝 Quiz Zone", "🔖 Bookmarks", "🏆 Achievements"])

# ---------------------------------------------------------------------------
# TAB 1 — Dashboard
# ---------------------------------------------------------------------------
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total XP", st.session_state.xp)
    c2.metric("Interactions", len(st.session_state.chat_history))
    c3.metric("Bookmarks", len(st.session_state.bookmarks))
    c4.metric("Badges Earned", len(st.session_state.badges))

    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown("#### 🧑‍🏫 Meet Nova, your AI Buddy")
    st.write(PERSONA_DESCRIPTION)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown("#### 🚀 Quick Start")
    st.write(
        "Type a topic in the sidebar, pick an activity, and head to the "
        "**Learning Studio** tab to generate your first response. Try "
        "**Generate Quiz** in the Quiz Zone to start earning XP!"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.chat_history:
        st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
        st.markdown("#### 🕘 Recent Activity")
        for turn in st.session_state.chat_history[-5:][::-1]:
            st.markdown(f"**{turn['activity']}** — {turn['topic']} · _{turn['ts']}_")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 2 — Learning Studio (core chat / activity interface)
# ---------------------------------------------------------------------------
with tabs[1]:
    topic = st.session_state.current_topic
    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown(f"##### Selected activity: <span class='lb-pill'>{activity}</span>", unsafe_allow_html=True)

    extra_input = ""
    if activity == "Ask Anything":
        extra_input = st.text_input("Your question", placeholder="Ask Nova anything about this topic...")

    run_full_session = st.checkbox("Run as a full learning session instead (explain + example + quiz)")

    generate = st.button("✨ Generate", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if generate:
        if not topic.strip():
            st.warning("Please enter a topic in the sidebar first.")
        else:
            with st.spinner("Nova is thinking..."):
                if run_full_session:
                    result = call_gemini(prompt_full_session(topic))
                    used_activity = "Full Learning Session"
                else:
                    builder = ACTIVITY_PROMPT_MAP.get(activity)
                    prompt_text = builder(topic, question=extra_input) if builder else topic
                    result = call_gemini(prompt_text)
                    used_activity = activity
            add_to_history(used_activity, topic, result)
            award_xp(10)
            st.rerun()

    if st.session_state.chat_history:
        st.markdown("#### 💬 Conversation")
        for i, turn in enumerate(st.session_state.chat_history[::-1]):
            with st.expander(f"{turn['activity']} — {turn['topic']} ({turn['ts']})", expanded=(i == 0)):
                st.write(turn["content"])
                bcol1, bcol2 = st.columns([1, 4])
                with bcol1:
                    if st.button("🔖 Bookmark", key=f"bm_{i}_{turn['ts']}"):
                        st.session_state.bookmarks.append(turn)
                        st.toast("Bookmarked!")

        st.divider()
        transcript = build_transcript(topic or "Untitled")
        st.download_button(
            "⬇️ Download Notes (transcript)",
            data=as_download_bytes(transcript),
            file_name=f"{(topic or 'session').replace(' ', '_')}_notes.txt",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# TAB 3 — Quiz Zone (interactive: select answers, then submit to see results)
# ---------------------------------------------------------------------------
with tabs[2]:
    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown("#### 📝 Generate a Quiz")
    quiz_topic = st.text_input("Quiz topic", value=st.session_state.current_topic, key="quiz_topic_input")
    if st.button("Generate 5-Question Quiz", type="primary"):
        if not quiz_topic.strip():
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Building your quiz..."):
                quiz_raw = call_gemini(prompt_quiz(quiz_topic))
                parsed_quiz = parse_quiz_json(quiz_raw)

            if not parsed_quiz:
                st.error(
                    "Nova's quiz came back in an unexpected format — please "
                    "try generating it again."
                )
            else:
                # Fresh quiz: reset any previous answers/submission state.
                st.session_state.quiz_questions = parsed_quiz
                st.session_state.quiz_topic_name = quiz_topic
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.last_quiz_correct_count = 0
                add_to_history("Generate Quiz", quiz_topic, quiz_raw)
                award_xp(15)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    questions = st.session_state.quiz_questions
    if questions:
        st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
        st.markdown(f"#### Your Quiz — {st.session_state.quiz_topic_name}")

        if not st.session_state.quiz_submitted:
            # --- Selection phase: show clickable options, no results yet ---
            for i, q in enumerate(questions):
                st.markdown(f"**Q{i + 1}. {q['question']}**")
                letters = list(q["options"].keys())
                option_labels = [f"{letter}) {q['options'][letter]}" for letter in letters]

                previous_letter = st.session_state.quiz_answers.get(i)
                default_index = (
                    letters.index(previous_letter) if previous_letter in letters else None
                )

                choice = st.radio(
                    label=f"Question {i + 1} options",
                    options=option_labels,
                    index=default_index,
                    key=f"quiz_radio_{i}",
                    label_visibility="collapsed",
                )
                if choice:
                    st.session_state.quiz_answers[i] = choice.split(")", 1)[0].strip()
                st.write("")

            answered_count = len(st.session_state.quiz_answers)
            st.caption(f"Answered {answered_count} / {len(questions)} questions")

            if st.button("✅ Submit Quiz", type="primary", use_container_width=True):
                if answered_count < len(questions):
                    st.warning("Please answer every question before submitting.")
                else:
                    result = grade_quiz(questions, st.session_state.quiz_answers)
                    st.session_state.quiz_submitted = True
                    st.session_state.last_quiz_correct_count = result["correct_count"]
                    st.session_state.quiz_score["attempted"] += result["total"]
                    st.session_state.quiz_score["correct"] += result["correct_count"]
                    award_xp(result["correct_count"] * 5)
                    st.rerun()
        else:
            # --- Results phase: reveal correct/incorrect + explanations ---
            result = grade_quiz(questions, st.session_state.quiz_answers)
            correct_count = result["correct_count"]
            total = result["total"]
            pct = round(100 * correct_count / total) if total else 0

            if pct >= 80:
                st.success(f"🎉 Great job! You scored {correct_count} / {total} ({pct}%).")
            elif pct >= 50:
                st.info(f"👍 Nice effort — you scored {correct_count} / {total} ({pct}%).")
            else:
                st.warning(f"You scored {correct_count} / {total} ({pct}%). Let's review below.")

            st.divider()
            st.markdown("#### 📋 Review")
            for i, item in enumerate(result["breakdown"]):
                icon = "✅" if item["is_correct"] else "❌"
                st.markdown(f"{icon} **Q{i + 1}. {item['question']}**")

                picked = item["picked"]
                picked_text = item["options"].get(picked, "No answer selected")
                st.write(f"Your answer: **{picked}) {picked_text}**" if picked else "Your answer: _(skipped)_")

                if not item["is_correct"]:
                    correct_letter = item["correct_letter"]
                    correct_text = item["options"].get(correct_letter, "")
                    st.write(f"Correct answer: **{correct_letter}) {correct_text}**")

                if item["explanation"]:
                    st.caption(item["explanation"])
                st.write("")

            if st.button("🔁 Try Another Quiz", use_container_width=True):
                st.session_state.quiz_questions = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown("#### ✅ Check a Free-Form Answer")
    st.caption("Not from the quiz above? Paste any question + your answer for feedback.")
    q_text = st.text_area("Paste the question you're answering")
    your_answer = st.text_input("Your answer")
    if st.button("Evaluate My Answer"):
        if q_text.strip() and your_answer.strip():
            with st.spinner("Checking..."):
                feedback = call_gemini(prompt_evaluate(quiz_topic, q_text, your_answer))
            st.write(feedback)
            st.session_state.quiz_score["attempted"] += 1
            if "correct" in feedback.lower()[:60] or "✅" in feedback:
                st.session_state.quiz_score["correct"] += 1
            award_xp(5)
        else:
            st.warning("Fill in both the question and your answer.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 4 — Bookmarks
# ---------------------------------------------------------------------------
with tabs[3]:
    if not st.session_state.bookmarks:
        st.info("No bookmarks yet — bookmark responses from the Learning Studio tab.")
    else:
        search = st.text_input("🔍 Search bookmarks", placeholder="Search by topic or activity...")
        filtered = [
            b for b in st.session_state.bookmarks
            if search.lower() in b["topic"].lower() or search.lower() in b["activity"].lower()
        ] if search else st.session_state.bookmarks

        for i, b in enumerate(filtered):
            with st.expander(f"{b['activity']} — {b['topic']}"):
                st.write(b["content"])

        all_text = "\n\n---\n\n".join(f"{b['activity']} — {b['topic']}\n{b['content']}" for b in st.session_state.bookmarks)
        st.download_button("⬇️ Download All Bookmarks", data=as_download_bytes(all_text), file_name="bookmarks.txt")

# ---------------------------------------------------------------------------
# TAB 5 — Achievements
# ---------------------------------------------------------------------------
with tabs[4]:
    st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
    st.markdown("#### 🏆 Your Badges")
    if st.session_state.badges:
        st.markdown(
            "".join(f"<span class='lb-badge'>{b}</span>" for b in st.session_state.badges),
            unsafe_allow_html=True,
        )
    else:
        st.write("No badges yet — keep learning to earn your first one!")
    st.progress(min(st.session_state.xp / 600, 1.0), text=f"{st.session_state.xp} / 600 XP to max badge")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="lb-footer">
        Built with ❤️ using Streamlit & Google Gemini · AI Learning Buddy
    </div>
    """,
    unsafe_allow_html=True,
)