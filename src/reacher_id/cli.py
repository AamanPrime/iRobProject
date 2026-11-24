"""Command-line entry points for the complete Phase 1 pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import load_config
from .dataset import atomic_write_json, generate_dataset
from .environment import assert_runtime, inspect_runtime
from .validation import run_phase1_validation


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "phase1.toml"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_INSPECTION = PROJECT_ROOT / "artifacts" / "runtime_inspection.json"
DEFAULT_VALIDATION = PROJECT_ROOT / "artifacts" / "phase1_validation.json"


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reacher-phase1",
        description="Build and validate the reacher inverse-dynamics Phase 1 foundation.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect and assert the pinned runtime")
    inspect_parser.add_argument("--output", type=Path, default=DEFAULT_INSPECTION)

    generate_parser = subparsers.add_parser("generate", help="Generate the complete labeled dataset")
    generate_parser.add_argument("--output-dir", type=Path, default=DEFAULT_DATASET_DIR)
    generate_parser.add_argument("--force", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Run every Phase 1 acceptance check")
    validate_parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    validate_parser.add_argument("--output", type=Path, default=DEFAULT_VALIDATION)

    all_parser = subparsers.add_parser("all", help="Inspect, generate, and validate Phase 1")
    all_parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    all_parser.add_argument("--inspection-output", type=Path, default=DEFAULT_INSPECTION)
    all_parser.add_argument("--validation-output", type=Path, default=DEFAULT_VALIDATION)
    all_parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    if args.command == "inspect":
        info = inspect_runtime(config.runtime.seed)
        assert_runtime(info, config.runtime)
        payload = {"status": "passed", "runtime": info.to_dict()}
        atomic_write_json(args.output.resolve(), payload)
        _print(payload)
        return 0

    if args.command == "generate":
        metadata = generate_dataset(config, args.output_dir, overwrite=args.force)
        _print(metadata)
        return 0

    if args.command == "validate":
        report = run_phase1_validation(config, args.dataset_dir, args.output)
        _print(report)
        return 0

    if args.command == "all":
        info = inspect_runtime(config.runtime.seed)
        assert_runtime(info, config.runtime)
        inspection = {"status": "passed", "runtime": info.to_dict()}
        atomic_write_json(args.inspection_output.resolve(), inspection)
        generate_dataset(config, args.dataset_dir, overwrite=args.force)
        report = run_phase1_validation(config, args.dataset_dir, args.validation_output)
        _print(report)
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
