from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from analysis_service import SpeechAnalysisError, analyze_audio_path


AUDIENCE_OPTIONS = [
    "Executive stakeholders",
    "Technical team",
    "Classroom students",
    "Sales prospects",
    "Interview panel",
    "General audience",
    "Custom audience",
]

GOAL_OPTIONS = [
    "Inform",
    "Persuade",
    "Teach",
    "Pitch",
    "Interview answer",
    "Storytelling",
]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #0f172a;
            --muted: #52637a;
            --blue: #1d4ed8;
            --blue-soft: #dbeafe;
            --line: #d7e0ee;
            --panel: #ffffff;
            --page: #f3f7fc;
            --sidebar: #111827;
        }
        .stApp {
            background: var(--page);
            color: var(--ink);
        }
        .block-container {
            max-width: 1220px;
            padding-top: 1.15rem;
            padding-bottom: 2.5rem;
        }
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            letter-spacing: 0;
        }
        .hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.55rem 1.65rem;
            background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 18px 42px rgba(15,23,42,0.07);
            margin-bottom: 1.2rem;
        }
        .hero h1 {
            margin: 0;
            color: var(--ink);
            font-size: clamp(2rem, 5vw, 3.25rem);
            line-height: 1.02;
            font-weight: 850;
        }
        .hero p {
            color: var(--muted);
            margin: 0.7rem 0 0;
            font-size: 1rem;
        }
        .section-title {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 820;
            margin: 0.25rem 0 0.55rem;
        }
        .section-copy {
            color: var(--muted);
            margin: 0 0 1rem;
        }
        section[data-testid="stSidebar"] {
            background: var(--sidebar);
        }
        section[data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #cbd5e1 !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
        section[data-testid="stSidebar"] div[data-baseweb="textarea"] textarea {
            background: #020617 !important;
            border: 1px solid #334155 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border-radius: 8px !important;
        }
        section[data-testid="stSidebar"] textarea::placeholder {
            color: #94a3b8 !important;
            opacity: 1 !important;
        }
        section[data-testid="stSidebar"] [role="radiogroup"] label p {
            color: #ffffff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
            box-shadow: 0 12px 30px rgba(15,23,42,0.06);
        }
        div[data-testid="stFileUploader"] section {
            background: #ffffff !important;
            border: 1px dashed #93b4e5 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stFileUploader"] section * {
            color: var(--ink) !important;
        }
        div[data-testid="stFileUploader"] button,
        div[data-testid="stAudioInput"] button {
            color: var(--ink) !important;
            background: #eef5ff !important;
            border: 1px solid #bfd7ff !important;
            border-radius: 8px !important;
        }
        div[data-testid="stAlert"] {
            background: var(--blue-soft);
            border: 1px solid #bfdbfe;
            border-radius: 8px;
        }
        div[data-testid="stAlert"] * {
            color: #1e3a8a !important;
        }
        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.85rem;
            background: #ffffff;
        }
        div[data-testid="stMetric"] * {
            color: var(--ink) !important;
        }
        div[data-testid="stMetricLabel"] * {
            color: var(--muted) !important;
        }
        .stButton > button {
            background: var(--blue);
            border: 1px solid var(--blue);
            color: #ffffff !important;
            border-radius: 8px;
            min-height: 44px;
            font-weight: 750;
        }
        .stButton > button:disabled {
            background: #d8e2f0 !important;
            border-color: #d8e2f0 !important;
            color: #64748b !important;
            opacity: 1 !important;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li {
            color: var(--ink);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def uploaded_file_to_temp(uploaded_file, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name


def suffix_for_file(uploaded_file, fallback: str = ".wav") -> str:
    name = getattr(uploaded_file, "name", "") or ""
    suffix = Path(name).suffix
    return suffix if suffix else fallback


def render_results(result: dict) -> None:
    metrics = result.get("metrics", {})
    score = float(result.get("star_rating", 0))

    st.subheader("Speech Review")
    score_col, duration_col, pace_col, words_col, filler_col = st.columns(5)
    score_col.metric("Score", f"{score:.1f}/5")
    duration_col.metric("Duration", f"{metrics.get('duration_sec', 0):.0f}s")
    pace_col.metric("Pace", f"{metrics.get('pace_wpm', 0):.0f} WPM")
    words_col.metric("Words", metrics.get("total_words", 0))
    filler_col.metric("Fillers", metrics.get("filler_total", 0))

    st.markdown("#### Constructive Feedback")
    st.markdown(result.get("report", "No feedback returned."))

    pacing_data = result.get("pacing_data", [])
    if pacing_data:
        st.markdown("#### Pacing")
        st.line_chart(
            {
                "time_sec": [point["time"] for point in pacing_data],
                "wpm": [point["wpm"] for point in pacing_data],
            },
            x="time_sec",
            y="wpm",
        )

    filler_counts = result.get("filler_counts", {})
    if filler_counts:
        st.markdown("#### Filler Words")
        st.json(filler_counts, expanded=False)

    with st.expander("Transcript", expanded=False):
        st.write(result.get("transcript", "Transcript unavailable."))


def main() -> None:
    os.environ.setdefault("WHISPER_MODEL", "tiny")
    st.set_page_config(page_title="UDBHAV Speech Coach", layout="wide")
    inject_styles()

    st.markdown(
        """
        <section class="hero">
            <h1>UDBHAV Speech Coach</h1>
            <p>Local speech scoring for live recordings and uploaded speeches.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Speech Setup")
        audience = st.selectbox("Target audience", AUDIENCE_OPTIONS, index=5)
        speech_goal = st.selectbox("Speech goal", GOAL_OPTIONS)
        audience_detail = st.text_area("Audience context", placeholder="Optional context, expectations, or topic.")
        source = st.radio("Speech source", ["Live speech", "Recorded speech"])
        st.caption("Uses the local trained model. No Gemini key is required.")

    audio_input = None
    suffix = ".wav"

    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="section-title">Capture Speech</div>', unsafe_allow_html=True)
            st.markdown(
                '<p class="section-copy">Record directly in the browser or upload an existing audio file.</p>',
                unsafe_allow_html=True,
            )
            if source == "Live speech":
                audio_input = st.audio_input("Record live speech")
                suffix = ".wav"
            else:
                audio_input = st.file_uploader("Upload recorded speech", type=["wav", "mp3", "m4a", "ogg", "webm", "mp4"])
                if audio_input is not None:
                    suffix = suffix_for_file(audio_input)

            analyze_clicked = st.button("Analyze Speech", use_container_width=True, disabled=audio_input is None)

    with right:
        with st.container(border=True):
            st.markdown('<div class="section-title">Model Review</div>', unsafe_allow_html=True)
            if not analyze_clicked:
                st.info("Record or upload a speech to see the local model review here.")
            elif audio_input is None:
                st.warning("Please provide speech audio first.")
            else:
                tmp_path = ""
                try:
                    tmp_path = uploaded_file_to_temp(audio_input, suffix)
                    with st.spinner("Transcribing and scoring speech..."):
                        result = analyze_audio_path(
                            audio_file_path=tmp_path,
                            audience=audience,
                            speech_goal=speech_goal,
                            audience_detail=audience_detail,
                            input_source=source,
                        )
                    render_results(result)
                except SpeechAnalysisError as error:
                    st.error(str(error))
                except Exception as error:
                    st.error(f"Analysis failed: {error}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)


if __name__ == "__main__":
    main()
