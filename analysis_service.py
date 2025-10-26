import os
import re
import whisper
import torch
from pydub import AudioSegment
import google.generativeai as genai
import time
from flask import Flask, request, jsonify
import tempfile

# --- 1. NEW: DEFINE FILLER WORDS ---
# You can add or remove words from this set
FILLER_WORDS = {
    'um', 'uh', 'like', 'so', 'you know', 'actually', 'basically', 'right',
    'literally', 'i mean', 'kind of', 'sort of', 'well'
}

# --- 2. MODEL LOADING (Done once at startup) ---

def load_whisper_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    try:
        model = whisper.load_model("base", device=device)
        print("Whisper 'base' model loaded successfully.")
        return model
    except Exception as e:
        print(f"Failed to load Whisper model: {e}")
        return None

whisper_model = load_whisper_model()
if whisper_model is None:
    print("CRITICAL: Could not load Whisper model. Exiting.")
    exit(1)

# --- 3. AI ANALYSIS LOGIC (Unchanged) ---
def run_ai_analysis(transcript, duration_sec, api_key, audience):
    print("Sending transcript to AI for analysis...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
    except Exception as e:
        return f"Error creating AI model: {e}", 0

    if duration_sec == 0:
        return "Error: Audio duration is zero.", 0

    words = re.findall(r'\b\w+\b', transcript.lower())
    total_words = len(words)
    if total_words == 0:
        return "Error: No words detected in transcript.", 0

    wpm = (total_words / duration_sec) * 60

    system_prompt = (
        "You are an expert speech and presentation coach. "
        "Your first line of output MUST be a star rating in the format: Star Rating: X/5 (e.g., Star Rating: 3.5/5). "
        "After that line, provide constructive, encouraging, and actionable feedback."
    )
    
    user_prompt = f"""
    Please analyze the following speech transcript and its metadata.
    Provide a detailed, helpful critique as a speech coach.

    **Speech Context:**
    - Intended Audience: "{audience or 'Not specified'}"
    
    **Metadata:**
    - Speech Duration: {duration_sec:.2f} seconds
    - Total Words: {total_words}
    - Calculated Pace: {wpm:.0f} WPM

    **Transcript:**
    "{transcript}"

    **Your Analysis (Remember to provide audience-specific feedback):**
    ### 1. Pacing Analysis
    ### 2. Filler Word Analysis
    ### 3. Clarity and Conciseness
    ### 4. Key Improvement Tips (Tailored to the audience)
    """

    try:
        response = model.generate_content([system_prompt, user_prompt])
        full_report_text = response.text
        
        star_rating = 0.0
        cleaned_report = full_report_text
        
        match = re.search(r"Star Rating: (\d(\.\d)?)/5", full_report_text)
        if match:
            star_rating = float(match.group(1))
            cleaned_report = re.sub(r"Star Rating: .*\n?", "", full_report_text, 1).strip()
            
        return cleaned_report, star_rating
        
    except Exception as e:
        return f"Error during AI analysis: {e}", 0

# --- 4. AUDIO PROCESSING (***HEAVILY UPDATED***) ---
def process_audio_file(audio_file_path):
    try:
        audio_segment = AudioSegment.from_file(audio_file_path)
        duration_sec = audio_segment.duration_seconds
    except Exception as e:
        print(f"Error loading audio: {e}")
        return None, None, None, None

    try:
        print("Transcribing audio... (This will provide timestamps)")
        # We need the full result object, not just the text
        result = whisper_model.transcribe(audio_file_path, fp16=torch.cuda.is_available())
        
        full_transcript = result.get("text", "")
        if not full_transcript:
            return "", duration_sec, [], {"total": 0}

        # --- New: Pacing Analysis ---
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
            
            # Add a data point to our graph. We use 'end_time' as the x-axis.
            pacing_data.append({"time": round(end_time, 2), "wpm": round(wpm)})

        # --- New: Filler Word Count ---
        filler_counts = {"total": 0}
        # Use regex to find filler words, ignoring case
        for word in FILLER_WORDS:
            # Use \b to match whole words only
            matches = re.findall(r'\b' + re.escape(word) + r'\b', full_transcript, re.IGNORECASE)
            count = len(matches)
            if count > 0:
                filler_counts[word] = count
                filler_counts["total"] += count
        
        return full_transcript, duration_sec, pacing_data, filler_counts

    except Exception as e:
        print(f"Error during transcription: {e}")
        return None, None, None, None

# --- 5. FLASK WEB SERVER (***UPDATED***) ---
app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_speech():
    start_time = time.time()
    
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    api_key = request.form.get('api_key')
    if not api_key:
        return jsonify({"error": "No API key provided"}), 400
        
    audience = request.form.get('audience', 'A general audience')
    audio_file = request.files['audio_file']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=audio_file.filename) as tmp_file:
        audio_file.save(tmp_file.name)
        tmp_file_path = tmp_file.name

    try:
        # --- NEW: Get all the new data from our processing function ---
        transcript, duration_sec, pacing_data, filler_counts = process_audio_file(tmp_file_path)
        
        if transcript is None or duration_sec is None:
            return jsonify({"error": "Failed to process audio file."}), 500
        
        if not transcript:
            return jsonify({"error": "No speech detected in the audio."}), 400

        report, star_rating = run_ai_analysis(transcript, duration_sec, api_key, audience)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # --- NEW: Add pacing_data and filler_counts to the response ---
        return jsonify({
            "report": report,
            "star_rating": star_rating,
            "time_taken": f"{total_time:.2f}",
            "pacing_data": pacing_data,
            "filler_counts": filler_counts
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

if __name__ == '__main__':
    print("Starting Python AI Service on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)