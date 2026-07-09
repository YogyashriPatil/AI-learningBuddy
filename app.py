"""
app.py
------
AI Learning Buddy — main Streamlit application.

Run locally:
    streamlit run app.py

Requires a Gemini API key set via `.streamlit/secrets.toml` or the
`GEMINI_API_KEY` environment variable. See README.md for full deployment
instructions (Streamlit Cloud / local / Google Colab + ngrok).
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
# TAB 3 — Quiz Zone
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
                from prompts import prompt_quiz

                quiz_text = call_gemini(prompt_quiz(quiz_topic))
            st.session_state.last_quiz_raw = quiz_text
            add_to_history("Generate Quiz", quiz_topic, quiz_text)
            award_xp(15)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.last_quiz_raw:
        st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
        st.markdown("#### Your Quiz")
        st.write(st.session_state.last_quiz_raw)
        st.download_button(
            "⬇️ Download Quiz",
            data=as_download_bytes(st.session_state.last_quiz_raw),
            file_name=f"{(quiz_topic or 'quiz').replace(' ', '_')}_quiz.txt",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='lb-card'>", unsafe_allow_html=True)
        st.markdown("#### ✅ Check an Answer")
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