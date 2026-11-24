#!/usr/bin/env python3
"""Run runtime inspection, deterministic dataset generation, and validation."""

from reacher_id.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["all", "--force"]))
