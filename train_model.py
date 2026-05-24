from __future__ import annotations

import argparse
from pathlib import Path

from local_speech_model import DEFAULT_MODEL_PATH, FEATURE_NAMES, train_and_save_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the local UDBHAV speech scoring model.")
    parser.add_argument(
        "--data",
        help=(
            "Optional CSV with columns: score plus "
            + ", ".join(FEATURE_NAMES)
            + ". If omitted, a bootstrap training set is generated."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_MODEL_PATH),
        help="Where to save the trained model JSON artifact.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model = train_and_save_model(args.data, Path(args.output))
    print(f"Saved {model['version']} to {args.output}")
    print(f"Training records: {model['training']['records']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
