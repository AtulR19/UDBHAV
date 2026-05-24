from __future__ import annotations

import html
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
            --blue-2: #2563eb;
            --blue-soft: #dbeafe;
            --cyan: #0891b2;
            --green: #16a34a;
            --amber: #b45309;
            --line: #d6e1f1;
            --panel: #ffffff;
            --page: #f4f8fd;
            --sidebar: #0f172a;
        }
        .stApp {
            background:
                linear-gradient(180deg, rgba(244,248,253,0.96), rgba(255,255,255,0.98)),
                radial-gradient(circle at 10% 0%, rgba(37,99,235,0.12), transparent 30rem);
            color: var(--ink);
        }
        .block-container {
            max-width: 1240px;
            padding-top: 1.15rem;
            padding-bottom: 2.75rem;
        }
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            letter-spacing: 0;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li {
            color: var(--ink);
        }
        .hero {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.45rem 1.55rem;
            background:
                linear-gradient(135deg, #ffffff 0%, #f8fbff 70%),
                repeating-linear-gradient(90deg, rgba(37,99,235,0.05) 0 1px, transparent 1px 72px);
            box-shadow: 0 18px 42px rgba(15,23,42,0.07);
            margin-bottom: 1rem;
        }
        .hero::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--blue), var(--cyan), var(--green));
        }
        .hero-kicker {
            color: var(--blue);
            font-size: 0.78rem;
            font-weight: 850;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .hero h1 {
            margin: 0;
            color: var(--ink);
            font-size: clamp(2.1rem, 5vw, 3.65rem);
            line-height: 1.02;
            font-weight: 900;
        }
        .hero p {
            max-width: 760px;
            color: var(--muted);
            margin: 0.75rem 0 0;
            font-size: 1rem;
            line-height: 1.55;
        }
        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0.35rem 0.62rem;
            border-radius: 999px;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            background: #eff6ff;
            font-size: 0.82rem;
            font-weight: 760;
        }
        .section-title {
            color: var(--ink);
            font-size: 1.25rem;
            font-weight: 850;
            margin: 0.1rem 0 0.35rem;
        }
        .section-copy {
            color: var(--muted);
            margin: 0 0 1rem;
            line-height: 1.55;
        }
        .model-note {
            border: 1px solid #bfdbfe;
            border-left: 4px solid var(--blue);
            border-radius: 8px;
            padding: 0.85rem 0.9rem;
            background: #eff6ff;
            color: #1e3a8a;
            line-height: 1.5;
            margin-top: 0.3rem;
        }
        .score-band {
            display: grid;
            grid-template-columns: minmax(210px, 0.7fr) minmax(0, 1.3fr);
            gap: 1rem;
            align-items: stretch;
            margin: 1.1rem 0 1rem;
        }
        .score-card,
        .summary-card,
        .metric-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            box-shadow: 0 12px 30px rgba(15,23,42,0.06);
        }
        .score-card {
            padding: 1.1rem;
            background: linear-gradient(180deg, #ffffff, #eff6ff);
        }
        .score-label,
        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 850;
            text-transform: uppercase;
        }
        .score-value {
            color: var(--ink);
            font-size: clamp(2.4rem, 7vw, 4.2rem);
            line-height: 0.95;
            font-weight: 900;
            margin: 0.45rem 0 0.55rem;
        }
        .score-value span {
            color: var(--muted);
            font-size: 1.2rem;
            font-weight: 800;
        }
        .score-pill {
            display: inline-flex;
            border-radius: 999px;
            padding: 0.32rem 0.58rem;
            color: #ffffff;
            background: var(--blue);
            font-size: 0.86rem;
            font-weight: 800;
        }
        .summary-card {
            padding: 1.1rem;
        }
        .summary-card h2 {
            color: var(--ink);
            margin: 0 0 0.45rem;
            font-size: 1.55rem;
            line-height: 1.18;
        }
        .summary-card p {
            color: var(--muted);
            margin: 0;
            line-height: 1.55;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1.1rem;
        }
        .metric-card {
            padding: 0.85rem 0.9rem;
        }
        .metric-value {
            color: var(--ink);
            font-size: 1.55rem;
            font-weight: 880;
            margin-top: 0.35rem;
            white-space: normal;
            overflow-wrap: anywhere;
        }
        .filler-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.55rem 0 0.8rem;
        }
        .filler-chip {
            border: 1px solid #bfdbfe;
            border-radius: 999px;
            background: #eff6ff;
            color: #1e3a8a;
            padding: 0.38rem 0.62rem;
            font-size: 0.88rem;
            font-weight: 760;
        }
        .empty-review {
            border: 1px dashed #9fb9df;
            border-radius: 8px;
            padding: 1.2rem;
            background: rgba(255,255,255,0.72);
            color: var(--muted);
            text-align: center;
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
        div[data-testid="stMetric"] * {
            color: var(--ink) !important;
        }
        .stButton > button {
            background: var(--blue);
            border: 1px solid var(--blue);
            color: #ffffff !important;
            border-radius: 8px;
            min-height: 44px;
            font-weight: 780;
        }
        .stButton > button:disabled {
            background: #d8e2f0 !important;
            border-color: #d8e2f0 !important;
            color: #64748b !important;
            opacity: 1 !important;
        }
        @media (max-width: 900px) {
            .score-band,
            .metric-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def score_label(score: float) -> str:
    if score >= 4.4:
        return "Excellent"
    if score >= 3.7:
        return "Strong"
    if score >= 3.0:
        return "Developing"
    if score >= 2.2:
        return "Needs Focus"
    return "Practice Needed"


def metric_card(label: str, value: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{html.escape(label)}</div>
        <div class="metric-value">{html.escape(value)}</div>
    </div>
    """


def uploaded_file_to_temp(uploaded_file, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name


def suffix_for_file(uploaded_file, fallback: str = ".wav") -> str:
    name = getattr(uploaded_file, "name", "") or ""
    suffix = Path(name).suffix
    return suffix if suffix else fallback


def render_metric_grid(metrics: dict, filler_counts: dict, score: float) -> None:
    duration = float(metrics.get("duration_sec", 0) or 0)
    pace = float(metrics.get("pace_wpm", 0) or 0)
    words = int(metrics.get("total_words", 0) or 0)
    fillers = int(metrics.get("filler_total", filler_counts.get("total", 0)) or 0)

    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Duration", f"{duration:.0f}s")}
            {metric_card("Pace", f"{pace:.0f} WPM")}
            {metric_card("Words", f"{words:,}")}
            {metric_card("Fillers", f"{fillers:,}")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filler_chips(filler_counts: dict) -> None:
    if not filler_counts or not filler_counts.get("total"):
        st.markdown('<div class="filler-chip">No significant filler words detected</div>', unsafe_allow_html=True)
        return

    chips = [f'<span class="filler-chip">Total: {int(filler_counts.get("total", 0))}</span>']
    for word, count in sorted(filler_counts.items(), key=lambda item: item[1], reverse=True):
        if word != "total" and count:
            chips.append(f'<span class="filler-chip">{html.escape(str(word))}: {int(count)}</span>')
    st.markdown(f'<div class="filler-grid">{"".join(chips)}</div>', unsafe_allow_html=True)


def render_results(result: dict) -> None:
    metrics = result.get("metrics", {})
    filler_counts = result.get("filler_counts", {})
    score = float(result.get("star_rating", 0) or 0)
    audience = metrics.get("audience", "General audience")
    speech_goal = metrics.get("speech_goal", "Not specified")
    model_version = metrics.get("model_version", result.get("model", {}).get("version", "local-model"))

    st.markdown(
        f"""
        <div class="score-band">
            <div class="score-card">
                <div class="score-label">Overall Score</div>
                <div class="score-value">{score:.1f}<span>/5</span></div>
                <span class="score-pill">{html.escape(score_label(score))}</span>
            </div>
            <div class="summary-card">
                <h2>Speech Review</h2>
                <p>
                    Reviewed for <strong>{html.escape(str(audience))}</strong> with the goal
                    <strong>{html.escape(str(speech_goal))}</strong>. The local model version is
                    <strong>{html.escape(str(model_version))}</strong>.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_metric_grid(metrics, filler_counts, score)

    feedback_tab, pacing_tab, transcript_tab = st.tabs(["Coach Feedback", "Pacing & Fillers", "Transcript"])
    with feedback_tab:
        st.markdown(result.get("report", "No feedback returned."))

    with pacing_tab:
        pacing_data = result.get("pacing_data", [])
        if pacing_data:
            st.line_chart(
                {
                    "time_sec": [point["time"] for point in pacing_data],
                    "wpm": [point["wpm"] for point in pacing_data],
                },
                x="time_sec",
                y="wpm",
            )
        else:
            st.info("No pacing data was returned for this speech.")

        st.markdown("#### Filler Words")
        render_filler_chips(filler_counts)

    with transcript_tab:
        st.write(result.get("transcript", "Transcript unavailable."))


def analyze_speech(audio_input, suffix: str, audience: str, speech_goal: str, audience_detail: str, source: str) -> None:
    tmp_path = ""
    try:
        tmp_path = uploaded_file_to_temp(audio_input, suffix)
        with st.spinner("Transcribing and scoring speech..."):
            st.session_state["last_result"] = analyze_audio_path(
                audio_file_path=tmp_path,
                audience=audience,
                speech_goal=speech_goal,
                audience_detail=audience_detail,
                input_source=source,
            )
            st.session_state["last_error"] = ""
    except SpeechAnalysisError as error:
        st.session_state["last_error"] = str(error)
        st.session_state.pop("last_result", None)
    except Exception as error:
        st.session_state["last_error"] = f"Analysis failed: {error}"
        st.session_state.pop("last_result", None)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def main() -> None:
    os.environ.setdefault("WHISPER_MODEL", "tiny")
    st.set_page_config(page_title="UDBHAV Speech Coach", layout="wide", initial_sidebar_state="expanded")
    inject_styles()

    st.markdown(
        """
        <section class="hero">
            <div class="hero-kicker">Local speech intelligence</div>
            <h1>UDBHAV Speech Coach</h1>
            <p>
                Record or upload a speech, then review audience fit, pacing, filler words,
                transcript quality, and a local model score in one polished coaching workspace.
            </p>
            <div class="chip-row">
                <span class="chip">No API key</span>
                <span class="chip">Live + uploaded speech</span>
                <span class="chip">Local trained model</span>
                <span class="chip">Whisper transcription</span>
            </div>
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

    setup_col, context_col = st.columns([1.05, 0.95], gap="large")
    with setup_col:
        with st.container(border=True):
            st.markdown('<div class="section-title">Capture Speech</div>', unsafe_allow_html=True)
            st.markdown(
                '<p class="section-copy">Use the microphone for a fresh take or upload a recorded practice speech.</p>',
                unsafe_allow_html=True,
            )
            if source == "Live speech":
                audio_input = st.audio_input("Record live speech")
                suffix = ".wav"
            else:
                audio_input = st.file_uploader(
                    "Upload recorded speech",
                    type=["wav", "mp3", "m4a", "ogg", "webm", "mp4"],
                )
                if audio_input is not None:
                    suffix = suffix_for_file(audio_input)

            analyze_clicked = st.button("Analyze Speech", use_container_width=True, disabled=audio_input is None)

    with context_col:
        with st.container(border=True):
            st.markdown('<div class="section-title">Review Profile</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="model-note">
                    <strong>Audience:</strong> {html.escape(audience)}<br>
                    <strong>Goal:</strong> {html.escape(speech_goal)}<br>
                    <strong>Source:</strong> {html.escape(source)}<br>
                    <strong>Model:</strong> Local scoring model with Whisper tiny transcription
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p class="section-copy" style="margin-top: 0.9rem;">The full review appears below after analysis, so results have room to breathe.</p>',
                unsafe_allow_html=True,
            )

    if analyze_clicked and audio_input is not None:
        analyze_speech(audio_input, suffix, audience, speech_goal, audience_detail, source)

    st.markdown("### Analysis Report")
    if st.session_state.get("last_error"):
        st.error(st.session_state["last_error"])
    elif st.session_state.get("last_result"):
        render_results(st.session_state["last_result"])
    else:
        st.markdown(
            """
            <div class="empty-review">
                Your full speech review will appear here after you record or upload audio.
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
