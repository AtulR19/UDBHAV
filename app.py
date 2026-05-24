from __future__ import annotations

import os
import site
import sys
import tempfile
from pathlib import Path

USER_SITE = site.getusersitepackages()
if USER_SITE and os.path.isdir(USER_SITE) and USER_SITE not in sys.path:
    sys.path.append(USER_SITE)

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from analysis_service import SpeechAnalysisError, analyze_audio_path


PROJECT_ROOT = Path(__file__).resolve().parent
MAX_UPLOAD_SIZE = 50 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


@app.get("/")
def index():
    return send_file(PROJECT_ROOT / "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error):
    return jsonify({"error": "Audio file is too large. Upload a file under 50 MB."}), 413


@app.post("/analyze")
def analyze_speech():
    if "audio_file" not in request.files:
        return jsonify({"error": "No audio file uploaded."}), 400

    audio_file = request.files["audio_file"]
    _, extension = os.path.splitext(audio_file.filename or "speech.webm")
    suffix = extension if extension else ".webm"
    tmp_file_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            audio_file.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        payload = analyze_audio_path(
            audio_file_path=tmp_file_path,
            audience=request.form.get("audience", "General audience"),
            speech_goal=request.form.get("speech_goal", ""),
            audience_detail=request.form.get("audience_detail", ""),
            input_source=request.form.get("input_source", ""),
        )
        return jsonify(payload)
    except SpeechAnalysisError as error:
        return jsonify({"error": str(error)}), error.status_code
    except Exception as error:
        return jsonify({"error": f"Analysis failed: {error}"}), 500
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


def main():
    port = int(os.environ.get("PORT", "3000"))
    print(f"Starting UDBHAV Speech Coach on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
