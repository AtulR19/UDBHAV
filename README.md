# UDBHAV Speech Coach

UDBHAV Speech Coach is a local AI speech review app. It accepts live microphone recordings or uploaded speech audio, transcribes the speech with Whisper, and rates delivery with a trainable local scoring model.

## Features

- Professional blue and white single-page interface
- Live microphone recording with preview playback
- Recorded speech upload for existing audio files
- Audience profile and speech goal selection
- Local trained star rating with constructive coaching feedback
- Transcript, pace, filler word, and duration metrics
- Canvas-based pacing chart with no frontend chart dependency
- `app.py` entry point for running the full app
- `train_model.py` entry point for training or retraining the local model

## Requirements

- Python 3.10 or newer
- FFmpeg installed and available on your system path

## Install

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Whisper uses FFmpeg to read audio. If transcription fails, confirm that `ffmpeg` works from your terminal.

## Train The Local Model

Create the default local model artifact:

```bash
python train_model.py
```

This writes:

```text
models/speech_score_model.json
```

The default training command uses a bootstrap speech-quality dataset so the app works immediately. When you collect your own labeled examples, train with a CSV:

```bash
python train_model.py --data data/my_speech_scores.csv
```

Custom CSV files must include a `score` column plus these feature columns:

```text
pace_quality,filler_control,pacing_consistency,structure_signal,lexical_range,sentence_control,duration_fit,audience_context,goal_signal
```

Each feature should be a value from `0` to `1`; `score` should be from `1` to `5`.

## Run

Start the app:

```bash
python app.py
```

Open:

```text
http://localhost:3000
```

## Deploy

The recommended deployment path is Docker because the app needs Python, Torch, Whisper, and FFmpeg.
The included Docker image installs FFmpeg, installs Python dependencies, keeps your trained local model, and caches the Whisper model during build.
The default deployment model is `tiny` Whisper to reduce memory usage. For better transcription quality on larger machines, set `WHISPER_MODEL=base`.

### Deploy On Render

1. Push this project to GitHub.
2. Create a new Render Blueprint or Web Service from the repo.
3. Use the included `render.yaml` when creating a Blueprint, or choose Docker as the runtime.
4. Set the health check path to:

```text
/health
```

Render will use:

```text
Dockerfile
render.yaml
```

Use a plan with enough memory for Torch and Whisper. Very small free instances may fail or time out on transcription.

### Deploy Anywhere With Docker

Build:

```bash
docker build -t udbhav-speech-coach .
```

Run:

```bash
docker run --rm -p 3000:3000 -e PORT=3000 udbhav-speech-coach
```

Open:

```text
http://localhost:3000
```

For platforms such as Railway, Fly.io, Azure Container Apps, or Google Cloud Run, deploy the Dockerfile and expose the platform-provided `PORT` environment variable.

## Usage

1. Pick a target audience and speech goal.
2. Choose `Live speech` to record in the browser, or `Recorded speech` to upload an audio file.
3. Submit the speech for analysis.
4. Review the local model score, coaching feedback, transcript, pacing chart, and filler word breakdown.

## Project Structure

```text
app.py                 Flask entry point for the full web app
index.html             Frontend UI and browser recording logic
analysis_service.py    Whisper transcription and local analysis workflow
local_speech_model.py  Local scoring model, features, feedback, and trainer helpers
train_model.py         Command line model training script
requirements.txt       Python dependencies
Dockerfile             Production container with FFmpeg and Whisper support
render.yaml            Render Blueprint deployment config
models/                Trained local model artifacts
```

## Notes

- No Gemini key or external LLM API is required.
- The included local model is a practical bootstrap model. For production-quality coaching, collect real speeches with human ratings and retrain with `train_model.py --data`.
- Large audio files can take several minutes depending on CPU/GPU speed.
- If a host runs out of memory, keep `WHISPER_MODEL=tiny` or choose a service with at least 2 GB RAM.
- Browser microphone recording requires HTTPS or localhost.
