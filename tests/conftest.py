from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("LC_ALL", "C.UTF-8")

from reacher_id.config import Phase1Config, load_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def phase1_config() -> Phase1Config:
    return load_config(PROJECT_ROOT / "configs" / "phase1.toml")
