from __future__ import annotations

import csv
import json
import math
import random
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "speech_score_model.json"

FEATURE_NAMES = [
    "pace_quality",
    "filler_control",
    "pacing_consistency",
    "structure_signal",
    "lexical_range",
    "sentence_control",
    "duration_fit",
    "audience_context",
    "goal_signal",
]

STRUCTURE_MARKERS = {
    "first", "second", "third", "finally", "because", "therefore", "however",
    "for example", "in conclusion", "to summarize", "the key point", "next",
}

GOAL_MARKERS = {
    "Inform": {"because", "therefore", "key", "reason", "data", "result"},
    "Persuade": {"should", "must", "benefit", "value", "evidence", "impact"},
    "Teach": {"first", "example", "means", "remember", "step", "practice"},
    "Pitch": {"problem", "solution", "market", "value", "customer", "growth"},
    "Interview answer": {"situation", "task", "action", "result", "learned"},
    "Storytelling": {"when", "then", "felt", "realized", "moment", "changed"},
}

AUDIENCE_TIPS = {
    "Executive stakeholders": "Lead with the business outcome, quantify impact early, and end with a clear decision or ask.",
    "Technical team": "Add concrete evidence, define assumptions, and call out tradeoffs so technical listeners can trust the reasoning.",
    "Classroom students": "Use signposts, examples, and a slightly slower pace so learners can follow the idea step by step.",
    "Sales prospects": "Tie each point to the listener's pain, proof, and value instead of only describing features.",
    "Interview panel": "Use a tight situation-task-action-result structure and keep each answer focused on the role.",
    "General audience": "Use plain language, clear transitions, and one memorable takeaway.",
    "Custom audience": "Make the audience need explicit and connect the main message to that need.",
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def split_sentences(text: str) -> list[str]:
    sentences = [sentence.strip() for sentence in re.split(r"[.!?]+", text) if sentence.strip()]
    return sentences or [text.strip()] if text.strip() else []


def count_phrases(text: str, phrases: set[str]) -> int:
    lowered = text.lower()
    return sum(len(re.findall(r"\b" + re.escape(phrase) + r"\b", lowered)) for phrase in phrases)


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def quality_from_distance(value: float, target: float, tolerance: float) -> float:
    if tolerance <= 0:
        return 0.0
    return clamp(1.0 - abs(value - target) / tolerance, 0.0, 1.0)


def extract_quality_features(
    transcript: str,
    duration_sec: float,
    pacing_data: list[dict],
    filler_counts: dict,
    audience: str,
    speech_goal: str,
    audience_detail: str,
) -> tuple[dict[str, float], dict[str, float]]:
    words = tokenize(transcript)
    word_count = len(words)
    unique_words = len(set(words))
    duration_sec = max(float(duration_sec or 0), 1.0)
    pace_wpm = (word_count / duration_sec) * 60
    filler_total = int((filler_counts or {}).get("total", 0))
    filler_rate = (filler_total / max(word_count, 1)) * 100

    wpm_values = [float(point.get("wpm", 0)) for point in pacing_data or [] if point.get("wpm")]
    pacing_variability = stddev(wpm_values)

    sentences = split_sentences(transcript)
    avg_sentence_words = word_count / max(len(sentences), 1)
    lexical_diversity = unique_words / max(word_count, 1)

    structure_count = count_phrases(transcript, STRUCTURE_MARKERS)
    structure_rate = (structure_count / max(word_count, 1)) * 100

    goal_phrases = GOAL_MARKERS.get(speech_goal, set())
    goal_count = count_phrases(transcript, goal_phrases)
    goal_rate = (goal_count / max(word_count, 1)) * 100

    audience_context_words = len(tokenize(f"{audience} {audience_detail}"))

    raw_metrics = {
        "word_count": word_count,
        "pace_wpm": pace_wpm,
        "filler_rate_per_100_words": filler_rate,
        "pacing_variability_wpm": pacing_variability,
        "avg_sentence_words": avg_sentence_words,
        "lexical_diversity": lexical_diversity,
        "structure_marker_rate": structure_rate,
        "goal_marker_rate": goal_rate,
        "duration_sec": duration_sec,
        "audience_context_words": audience_context_words,
    }

    features = {
        "pace_quality": quality_from_distance(pace_wpm, 145, 90),
        "filler_control": clamp(1.0 - filler_rate / 12, 0.0, 1.0),
        "pacing_consistency": clamp(1.0 - pacing_variability / 90, 0.0, 1.0),
        "structure_signal": clamp(structure_rate / 4, 0.0, 1.0),
        "lexical_range": quality_from_distance(lexical_diversity, 0.56, 0.42),
        "sentence_control": quality_from_distance(avg_sentence_words, 18, 24),
        "duration_fit": clamp(duration_sec / 90, 0.0, 1.0) if duration_sec < 90 else clamp(1.0 - (duration_sec - 420) / 480, 0.3, 1.0),
        "audience_context": clamp(audience_context_words / 18, 0.0, 1.0),
        "goal_signal": clamp(goal_rate / 3, 0.0, 1.0),
    }
    return features, raw_metrics


def bootstrap_score(features: dict[str, float], noise: float = 0.0) -> float:
    weights = {
        "pace_quality": 0.17,
        "filler_control": 0.15,
        "pacing_consistency": 0.11,
        "structure_signal": 0.13,
        "lexical_range": 0.10,
        "sentence_control": 0.10,
        "duration_fit": 0.08,
        "audience_context": 0.08,
        "goal_signal": 0.08,
    }
    weighted_quality = sum(features[name] * weights[name] for name in FEATURE_NAMES)
    return clamp(1.0 + weighted_quality * 4.0 + noise, 1.0, 5.0)


def synthesize_training_records(count: int = 1600, seed: int = 42) -> list[dict[str, float]]:
    random.seed(seed)
    records = []
    for _ in range(count):
        features = {name: clamp(random.betavariate(2.2, 1.9), 0.0, 1.0) for name in FEATURE_NAMES}
        if random.random() < 0.25:
            weak_feature = random.choice(FEATURE_NAMES)
            features[weak_feature] = random.betavariate(1.1, 4.5)
        score = bootstrap_score(features, noise=random.gauss(0, 0.16))
        records.append({**features, "score": score})
    return records


def load_training_csv(path: Path) -> list[dict[str, float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "score" not in reader.fieldnames:
            raise ValueError("Training CSV must include a score column.")

        records = []
        for row in reader:
            record = {"score": float(row["score"])}
            for feature in FEATURE_NAMES:
                if feature not in row:
                    raise ValueError(f"Training CSV is missing feature column: {feature}")
                record[feature] = float(row[feature])
            records.append(record)
    if not records:
        raise ValueError("Training CSV did not contain any records.")
    return records


def fit_linear_model(records: list[dict[str, float]], epochs: int = 2200, learning_rate: float = 0.045) -> dict:
    means = {
        name: sum(record[name] for record in records) / len(records)
        for name in FEATURE_NAMES
    }
    stds = {}
    for name in FEATURE_NAMES:
        variance = sum((record[name] - means[name]) ** 2 for record in records) / len(records)
        stds[name] = math.sqrt(variance) or 1.0

    weights = {name: 0.0 for name in FEATURE_NAMES}
    bias = sum(record["score"] for record in records) / len(records)
    l2 = 0.01

    for _ in range(epochs):
        weight_grads = {name: 0.0 for name in FEATURE_NAMES}
        bias_grad = 0.0

        for record in records:
            transformed = {
                name: (record[name] - means[name]) / stds[name]
                for name in FEATURE_NAMES
            }
            prediction = bias + sum(weights[name] * transformed[name] for name in FEATURE_NAMES)
            error = prediction - record["score"]
            bias_grad += error
            for name in FEATURE_NAMES:
                weight_grads[name] += error * transformed[name] + l2 * weights[name]

        scale = 1.0 / len(records)
        bias -= learning_rate * bias_grad * scale
        for name in FEATURE_NAMES:
            weights[name] -= learning_rate * weight_grads[name] * scale

    return {
        "version": "local-linear-speech-coach-v1",
        "feature_names": FEATURE_NAMES,
        "means": means,
        "stds": stds,
        "weights": weights,
        "bias": bias,
        "training": {
            "records": len(records),
            "source": "bootstrap synthetic labels" if len(records) >= 1000 else "custom CSV",
        },
    }


def save_model(model: dict, model_path: Path = DEFAULT_MODEL_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")


def train_and_save_model(training_csv: str | None = None, model_path: Path = DEFAULT_MODEL_PATH) -> dict:
    records = load_training_csv(Path(training_csv)) if training_csv else synthesize_training_records()
    model = fit_linear_model(records)
    save_model(model, model_path)
    return model


def load_model(model_path: Path = DEFAULT_MODEL_PATH) -> dict:
    if not model_path.exists():
        return train_and_save_model(model_path=model_path)
    return json.loads(model_path.read_text(encoding="utf-8"))


def predict_score(features: dict[str, float], model: dict) -> float:
    score = float(model["bias"])
    for name in model["feature_names"]:
        transformed = (features[name] - model["means"][name]) / model["stds"][name]
        score += model["weights"][name] * transformed
    return clamp(score, 1.0, 5.0)


def rating_label(score: float) -> str:
    if score >= 4.4:
        return "Excellent"
    if score >= 3.7:
        return "Strong"
    if score >= 3.0:
        return "Developing"
    if score >= 2.2:
        return "Needs focus"
    return "Needs major practice"


def weakest_features(features: dict[str, float], count: int = 3) -> list[tuple[str, float]]:
    return sorted(features.items(), key=lambda item: item[1])[:count]


def strongest_features(features: dict[str, float], count: int = 2) -> list[tuple[str, float]]:
    return sorted(features.items(), key=lambda item: item[1], reverse=True)[:count]


def feature_display_name(name: str) -> str:
    return name.replace("_", " ").title()


def build_feedback(
    score: float,
    features: dict[str, float],
    raw_metrics: dict[str, float],
    audience: str,
    speech_goal: str,
) -> str:
    strengths = strongest_features(features)
    improvements = weakest_features(features)
    pace = raw_metrics["pace_wpm"]
    filler_rate = raw_metrics["filler_rate_per_100_words"]
    avg_sentence_words = raw_metrics["avg_sentence_words"]

    pace_tip = "Your pace is in a comfortable range."
    if pace < 120:
        pace_tip = "Your pace is slow for most settings; practice adding energy while preserving clarity."
    elif pace > 175:
        pace_tip = "Your pace is fast; add short pauses after key claims so the audience can absorb them."

    filler_tip = "Filler control is solid."
    if filler_rate > 6:
        filler_tip = "Filler words are high; replace them with silent pauses and restart sentences deliberately."
    elif filler_rate > 3:
        filler_tip = "Filler words are noticeable; rehearse transitions so fewer words are used as bridges."

    sentence_tip = "Sentence length is manageable."
    if avg_sentence_words > 26:
        sentence_tip = "Several sentences are long; split complex points into shorter spoken units."
    elif avg_sentence_words < 8:
        sentence_tip = "Sentences are very short; connect related ideas so the speech feels less fragmented."

    audience_tip = AUDIENCE_TIPS.get(audience, AUDIENCE_TIPS["Custom audience"])
    improvement_lines = "\n".join(
        f"- {feature_display_name(name)}: {value:.0%}. Practice this area first."
        for name, value in improvements
    )
    strength_lines = "\n".join(
        f"- {feature_display_name(name)}: {value:.0%}."
        for name, value in strengths
    )

    return f"""### Score Rationale
The local speech model rated this as {score:.1f}/5 ({rating_label(score)}). The score is based on delivery features extracted from the transcript and audio timing, not an external API.

### Audience Fit
Target audience: {audience or "General audience"}.
Speech goal: {speech_goal or "Not specified"}.
{audience_tip}

### Delivery Strengths
{strength_lines}

### Improvements
{improvement_lines}

### Coaching Notes
- {pace_tip}
- {filler_tip}
- {sentence_tip}

### Practice Plan
Record one shorter take focused only on your weakest feature. Then record a second take with a clear opening claim, two supporting points, and a closing takeaway for the target audience."""


def analyze_with_local_model(
    transcript: str,
    duration_sec: float,
    pacing_data: list[dict],
    filler_counts: dict,
    audience: str,
    speech_goal: str,
    audience_detail: str,
) -> tuple[str, float, dict[str, float], dict[str, float], dict]:
    model = load_model()
    features, raw_metrics = extract_quality_features(
        transcript=transcript,
        duration_sec=duration_sec,
        pacing_data=pacing_data,
        filler_counts=filler_counts,
        audience=audience,
        speech_goal=speech_goal,
        audience_detail=audience_detail,
    )
    score = predict_score(features, model)
    report = build_feedback(score, features, raw_metrics, audience, speech_goal)
    return report, score, features, raw_metrics, model
