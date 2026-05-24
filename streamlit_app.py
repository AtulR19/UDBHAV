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
            --muted: #64748b;
            --blue: #2563eb;
            --line: #dbe3ef;
            --soft: #eff6ff;
        }
        .stApp {
            background:
                linear-gradient(180deg, rgba(239,246,255,0.94), rgba(255,255,255,0.97)),
                radial-gradient(circle at top left, rgba(37,99,235,0.16), transparent 34%);
            color: var(--ink);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
        }
        .hero {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.25rem 1.35rem;
            background: rgba(255,255,255,0.94);
            box-shadow: 0 20px 55px rgba(15,23,42,0.08);
            margin-bottom: 1.1rem;
        }
        .hero h1 {
            margin: 0;
            color: var(--ink);
            font-size: clamp(2rem, 5vw, 3.5rem);
            line-height: 1;
        }
        .hero p {
            color: var(--muted);
            margin: 0.65rem 0 0;
            font-size: 1rem;
        }
        .panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(255,255,255,0.94);
        }
        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.85rem;
            background: #ffffff;
        }
        .stButton > button {
            background: var(--blue);
            border: 1px solid var(--blue);
            color: white;
            border-radius: 8px;
            min-height: 44px;
            font-weight: 750;
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
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Capture Speech")
        if source == "Live speech":
            audio_input = st.audio_input("Record live speech")
            suffix = ".wav"
        else:
            audio_input = st.file_uploader("Upload recorded speech", type=["wav", "mp3", "m4a", "ogg", "webm", "mp4"])
            if audio_input is not None:
                suffix = suffix_for_file(audio_input)

        analyze_clicked = st.button("Analyze Speech", use_container_width=True, disabled=audio_input is None)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
