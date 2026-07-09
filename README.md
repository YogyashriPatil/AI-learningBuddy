# 🎓 AI Learning Buddy

A polished, Gemini-powered Streamlit study companion — built to satisfy every
requirement in the **Student Guide** and **Assignment Submission Guidelines**,
plus a set of extra study tools on top.

---

## 1. Project Structure

```
ai_learning_buddy/
├── app.py             # Main Streamlit app (UI + routing)
├── config.py           # Constants, activity lists, theme palettes
├── prompts.py          # Persona, system prompt, 5 required templates + extras
├── utils.py             # Gemini API wrapper, session state, download helpers
├── style.css            # Glassmorphism / gradient custom styling
├── requirements.txt
├── assets/               # Place any images/icons here
└── README.md            # This file
```

## 2. Setup — Local Machine

```bash
pip install -r requirements.txt
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "your-real-key-here"' > .streamlit/secrets.toml
streamlit run app.py
```
Open the URL Streamlit prints (usually `http://localhost:8501`).

## 3. Setup — Streamlit Community Cloud

1. Push this folder to a **public GitHub repo** (don't commit `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, click **New app**.
3. Point it at your repo, branch, and `app.py`.
4. In **Advanced settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "your-real-key-here"
   ```
5. Click **Deploy**. Copy the public `*.streamlit.app` URL — this is your
   mandatory submission link.

## 4. Setup — Google Colab + ngrok (as in the Student Guide)

```python
!pip install -q streamlit pyngrok google-generativeai
```
Upload `app.py`, `config.py`, `prompts.py`, `utils.py`, and `style.css` to
the Colab file browser (or `%%writefile` each one), then:
```python
import os
os.environ["GEMINI_API_KEY"] = "your-real-key-here"   # never commit this

!nohup streamlit run app.py --server.port 8501 &
import time; time.sleep(10)
!cat nohup.out

from pyngrok import ngrok
ngrok.set_auth_token("your-ngrok-token-here")
public_url = ngrok.connect(8501)
print(public_url)
```
Open the printed link. Remember: regenerate any key you ever paste into a
notebook you plan to share.

⚠️ **Never hardcode your API key in `app.py`.** This app only reads it from
`st.secrets` or the `GEMINI_API_KEY` environment variable.

---

## 5. Assignment Deliverables

### 5.1 Topic Selected
**Binary Search** — specific and well-scoped, per the guide's own advice
("Binary Search works better than Algorithms").

### 5.2 AI Buddy Persona
See `prompts.py :: PERSONA_DESCRIPTION` — Nova, a patient, encouraging
beginner-focused tutor. Full system prompt is in `prompts.py :: SYSTEM_PROMPT`.

### 5.3 Five Reusable Prompt Templates
Defined in `prompts.py`, all topic-agnostic (swap `{topic}` for anything):

1. `prompt_explain(topic)` — simple explanation
2. `prompt_example(topic)` — one real-life example
3. `prompt_quiz(topic, num_questions)` — 5-question MCQ quiz with answers
4. `prompt_evaluate(topic, question, learner_answer)` — feedback on a learner's answer (uses a few-shot example internally)
5. `prompt_full_session(topic)` — explain + example + quiz in one session

### 5.4 Sample Learning Conversation (Topic: Binary Search)

> **You:** Explain Concept — Binary Search
>
> **Nova:** Binary search is a fast way to find something in a *sorted* list
> by repeatedly cutting the search area in half. Imagine looking up a name
> in a phone book: instead of checking every page, you open to the middle,
> see if your name comes before or after it, and throw away the half you
> don't need — then repeat. Each step eliminates half of what's left, so
> it finds things much faster than checking one by one. It only works if
> the list is already sorted. **Key takeaway:** binary search trades a
> sorted list for massive speed — cutting the remaining options in half
> every single step.
>
> **You:** Real-Life Example — Binary Search
>
> **Nova:** Guessing a number between 1 and 100 when someone only tells you
> "higher" or "lower" is binary search in action — guessing 50 first,
> then 75 or 25 next, is exactly how the algorithm narrows down the answer
> in as few guesses as possible.
>
> **You:** Ask Anything — "Why can't I use binary search on an unsorted list?"
>
> **Nova:** Because binary search decides which half to discard based on
> comparing the middle value to your target — that logic only works if
> everything is arranged in order. On an unsorted list, the value you
> discard could actually be the one you wanted, so the algorithm would
> give wrong or missed results.

*(Full transcripts of your own sessions can be downloaded from the app's
"Download Notes" button in the Learning Studio tab.)*

### 5.5 Five-Question Quiz + Answers (Topic: Binary Search)

1. **What is the main requirement for binary search to work correctly?**
   A) The list must be sorted B) The list must be an array C) The list must have an even number of items D) The list must contain no duplicates
   **Answer: A** — Binary search relies on comparing to a midpoint and discarding a half; this logic breaks on unsorted data.

2. **What is the time complexity of binary search on a list of n items?**
   A) O(n) B) O(n²) C) O(log n) D) O(1)
   **Answer: C** — Each step halves the remaining list, giving logarithmic time.

3. **In binary search, what happens after comparing the target to the middle element?**
   A) The whole list is searched again B) One half of the list is discarded C) The list is re-sorted D) The search always ends
   **Answer: B** — The half that cannot contain the target is discarded.

4. **Which of these is the best real-world analogy for binary search?**
   A) Reading a book page by page B) Looking up a word in a dictionary by repeatedly opening to the middle C) Shuffling a deck of cards D) Searching a linked list from the head
   **Answer: B** — Both repeatedly narrow down a sorted range by checking the middle.

5. **If a sorted list has 1,000,000 items, roughly how many comparisons does binary search need in the worst case?**
   A) 1,000,000 B) 1,000 C) About 20 D) 2
   **Answer: C** — log₂(1,000,000) ≈ 20, illustrating how binary search scales.

*(Generate your own live quiz — with a different topic if you like — from
the Quiz Zone tab; it's produced fresh by Gemini and matches this format.)*

### 5.6 Reflection on AI Limitations (300–400 words) — **write this yourself**

This is the one deliverable that should come from you, not the AI — the
rubric specifically wants examples from *your own* sample conversation.
Use this outline as a starting point and fill it in with what you actually
noticed while testing the app:

- **Strengths (≈120 words):** What did Nova do well? Consider: clarity of
  the explanation you got, how well the real-life example matched the
  concept, how quickly you got a usable quiz. Reference a specific moment
  from your own transcript.
- **Limitations (≈150 words):** Where did the AI fall short? Consider:
  did any explanation feel generic or slightly off? Did it ever state
  something confidently that you had to double check? Could it explain
  *why* an answer was wrong, or just *that* it was wrong? Did it handle a
  topic outside its comfort zone well?
- **Improvements (≈100 words):** What would make a tool like this better?
  Consider: citing real sources, adapting difficulty to the learner's
  level over time, remembering what you've already learned, or flagging
  its own uncertainty more clearly.

Keep it in the 300–400 word range and use your own voice — this is what
graders can most easily tell was or wasn't genuinely written by you.

### 5.7 Streamlit App Link (Mandatory)
Deploy using Section 3 above, then paste your public `*.streamlit.app`
link here before submitting: `PASTE_YOUR_LIVE_APP_LINK_HERE`

---

## 6. Submission Checklist

- [ ] Topic selected and stated clearly
- [ ] Persona description + system prompt included
- [ ] All 5 reusable prompt templates included
- [ ] Sample learning conversation (full, coherent) included
- [ ] 5-question quiz with correct answers included
- [ ] Reflection written in your own words, 300–400 words, with specific examples
- [ ] Streamlit app deployed and link tested in a fresh/incognito browser tab
- [ ] Everything compiled into one document or shared folder
- [ ] Submitted via the assignment form: https://forms.gle/rLt4i4mmVpiyFQv79

## 7. Feature Overview

| Category | Features |
|---|---|
| Core | Explain Concept, Real-Life Example, Generate Quiz, Evaluate Answer, Ask Anything |
| Study Tools | Flashcards, Summary Generator, Revision Notes, Formula Sheet, Mnemonics, Text Mind Map |
| Career Prep | Interview Questions, Coding Questions |
| Explore | Related Topics, Further Reading, Common Mistakes, Learning Tips, Daily Challenge |
| UX | Sidebar navigation, dark/light mode, glassmorphism cards, animated transitions, loading spinners, responsive layout |
| Progress | XP, badges, quiz accuracy tracking, dashboard metrics |
| Data | Bookmarks with search, downloadable notes/quiz/transcripts, session state (no data leaves your session) |
| Reliability | Centralized error handling around every Gemini call, empty-input guards, cached model client |

## 8. Notes on Code Quality

- Type hints and docstrings throughout `utils.py` and `prompts.py`.
- Logic split into `config` / `prompts` / `utils` / `app` so each file has
  one clear responsibility (PEP 8, modular structure).
- All Gemini calls funnel through a single `call_gemini()` wrapper with
  try/except, so one bad response never crashes the app.
- API key is read only from `st.secrets` or environment variables — never
  hardcoded, per the Student Guide's explicit warning.