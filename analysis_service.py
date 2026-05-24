import os
import re
import site
import sys

USER_SITE = site.getusersitepackages()
if USER_SITE and os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.append(USER_SITE)

import whisper
import torch
from pydub import AudioSegment
import time

from local_speech_model import analyze_with_local_model

WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "tiny")

FILLER_WORDS = {
    'um', 'uh', 'like', 'so', 'you know', 'actually', 'basically', 'right',
    'literally', 'i mean', 'kind of', 'sort of', 'well'
}

def load_whisper_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    try:
        model = whisper.load_model(WHISPER_MODEL_NAME, device=device)
        print(f"Whisper '{WHISPER_MODEL_NAME}' model loaded successfully.")
        return model
    except Exception as e:
        print(f"Failed to load Whisper model: {e}")
        return None

whisper_model = None

class SpeechAnalysisError(Exception):
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = load_whisper_model()
    if whisper_model is None:
        raise SpeechAnalysisError("Could not load Whisper transcription model.", 500)
    return whisper_model

def process_audio_file(audio_file_path):
    try:
        audio_segment = AudioSegment.from_file(audio_file_path)
        duration_sec = audio_segment.duration_seconds
    except Exception as e:
        print(f"Error loading audio: {e}")
        return None, None, None, None

    try:
        print("Transcribing audio...")
        result = get_whisper_model().transcribe(audio_file_path, fp16=torch.cuda.is_available())
        
        full_transcript = result.get("text", "")
        if not full_transcript:
            return "", duration_sec, [], {"total": 0}

        pacing_data = []
        for segment in result.get("segments", []):
            segment_text = segment.get("text", "")
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            
            duration = end_time - start_time
            if duration == 0:
                continue

            words = re.findall(r'\b\w+\b', segment_text.lower())
            word_count = len(words)
            wpm = (word_count / duration) * 60
            
            pacing_data.append({"time": round(end_time, 2), "wpm": round(wpm)})

        filler_counts = {"total": 0}
        for word in FILLER_WORDS:
            matches = re.findall(r'\b' + re.escape(word) + r'\b', full_transcript, re.IGNORECASE)
            count = len(matches)
            if count > 0:
                filler_counts[word] = count
                filler_counts["total"] += count
        
        return full_transcript, duration_sec, pacing_data, filler_counts

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None, None, None, None

def analyze_audio_path(
    audio_file_path,
    audience="General audience",
    speech_goal="",
    audience_detail="",
    input_source="",
):
    start_time = time.time()
    transcript, duration_sec, pacing_data, filler_counts = process_audio_file(audio_file_path)

    if transcript is None or duration_sec is None:
        raise SpeechAnalysisError("Failed to process audio file.", 500)

    if not transcript:
        raise SpeechAnalysisError("No speech detected in the audio.", 400)

    words = re.findall(r'\b\w+\b', transcript.lower())
    total_words = len(words)
    pace_wpm = (total_words / duration_sec) * 60 if duration_sec else 0

    report, star_rating, quality_features, raw_metrics, model = analyze_with_local_model(
        transcript,
        duration_sec,
        pacing_data,
        filler_counts,
        audience,
        speech_goal,
        audience_detail
    )

    total_time = time.time() - start_time

    return {
        "report": report,
        "star_rating": star_rating,
        "time_taken": f"{total_time:.2f}",
        "transcript": transcript.strip(),
        "pacing_data": pacing_data,
        "filler_counts": filler_counts,
        "metrics": {
            "duration_sec": round(duration_sec, 2),
            "total_words": total_words,
            "pace_wpm": round(pace_wpm),
            "filler_total": filler_counts.get("total", 0),
            "audience": audience,
            "speech_goal": speech_goal,
            "input_source": input_source,
            "model_version": model.get("version", "local-model"),
            "quality_features": quality_features,
            "raw_features": raw_metrics
        },
        "model": {
            "version": model.get("version", "local-model"),
            "training": model.get("training", {})
        }
    }

if __name__ == '__main__':
    print("analysis_service.py contains reusable analysis logic. Run the app with: python app.py")
