"""Typed Phase 1 configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

import numpy as np


@dataclass(frozen=True)
class RuntimeConfig:
    domain: str
    task: str
    seed: int
    dm_control_version: str
    mujoco_version: str
    xml_sha256: str
    physics_timestep: float
    control_timestep: float
    torque_per_ctrl: float


@dataclass(frozen=True)
class DatasetConfig:
    duration_seconds: float
    sample_timestep: float
    train_trajectories: int
    validation_trajectories: int
    id_test_trajectories: int
    shoulder_ood_trajectories: int
    wrist_ood_trajectories: int
    trajectory_seed: int
    budget_seed: int
    torque_headroom: float
    constraint_tolerance: float
    max_generation_attempts: int
    fourier_components: int
    frequency_min_hz: float
    frequency_max_hz: float

    @property
    def samples_per_trajectory(self) -> int:
        ratio = self.duration_seconds / self.sample_timestep
        rounded = round(ratio)
        if not np.isclose(ratio, rounded, rtol=0.0, atol=1e-12):
            raise ValueError("duration_seconds must be divisible by sample_timestep")
        return int(rounded)

    @property
    def total_trajectories(self) -> int:
        return (
            self.train_trajectories
            + self.validation_trajectories
            + self.id_test_trajectories
            + self.shoulder_ood_trajectories
            + self.wrist_ood_trajectories
        )


@dataclass(frozen=True)
class EnvelopeConfig:
    q_low: np.ndarray
    q_high: np.ndarray
    max_abs_velocity: np.ndarray
    max_abs_acceleration: np.ndarray
    outside_joint: int | None = None
    outside_abs_min: float | None = None

    def __post_init__(self) -> None:
        for name in ("q_low", "q_high", "max_abs_velocity", "max_abs_acceleration"):
            value = np.asarray(getattr(self, name), dtype=np.float64)
            if value.shape != (2,):
                raise ValueError(f"{name} must have shape (2,), got {value.shape}")
            object.__setattr__(self, name, value)
        if np.any(self.q_low >= self.q_high):
            raise ValueError("Each q_low value must be less than q_high")
        if np.any(self.max_abs_velocity <= 0) or np.any(self.max_abs_acceleration <= 0):
            raise ValueError("Velocity and acceleration limits must be positive")
        if self.outside_joint is not None and self.outside_joint not in (0, 1):
            raise ValueError("outside_joint must be 0 or 1")


@dataclass(frozen=True)
class ValidationConfig:
    random_state_samples: int
    dataset_recheck_samples: int
    absolute_tolerance: float
    relative_tolerance: float
    seed: int


@dataclass(frozen=True)
class Phase1Config:
    runtime: RuntimeConfig
    dataset: DatasetConfig
    id_envelope: EnvelopeConfig
    shoulder_ood_envelope: EnvelopeConfig
    wrist_ood_envelope: EnvelopeConfig
    validation: ValidationConfig
    source_path: Path

    def envelope(self, regime: str) -> EnvelopeConfig:
        mapping = {
            "id": self.id_envelope,
            "shoulder_ood": self.shoulder_ood_envelope,
            "wrist_ood": self.wrist_ood_envelope,
        }
        try:
            return mapping[regime]
        except KeyError as exc:
            raise ValueError(f"Unknown trajectory regime: {regime}") from exc


def _envelope(section: dict) -> EnvelopeConfig:
    return EnvelopeConfig(
        q_low=np.asarray(section["q_low"], dtype=np.float64),
        q_high=np.asarray(section["q_high"], dtype=np.float64),
        max_abs_velocity=np.asarray(section["max_abs_velocity"], dtype=np.float64),
        max_abs_acceleration=np.asarray(section["max_abs_acceleration"], dtype=np.float64),
        outside_joint=section.get("outside_joint"),
        outside_abs_min=section.get("outside_abs_min"),
    )


def load_config(path: str | Path) -> Phase1Config:
    """Load and validate the Phase 1 TOML configuration."""
    source_path = Path(path).expanduser().resolve()
    with source_path.open("rb") as file:
        raw = tomllib.load(file)

    runtime = RuntimeConfig(**raw["runtime"])
    dataset = DatasetConfig(**raw["dataset"])
    validation = ValidationConfig(**raw["validation"])
    config = Phase1Config(
        runtime=runtime,
        dataset=dataset,
        id_envelope=_envelope(raw["envelope"]["id"]),
        shoulder_ood_envelope=_envelope(raw["envelope"]["shoulder_ood"]),
        wrist_ood_envelope=_envelope(raw["envelope"]["wrist_ood"]),
        validation=validation,
        source_path=source_path,
    )

    if dataset.sample_timestep != runtime.physics_timestep:
        raise ValueError("Dataset and physics timesteps must match in Phase 1")
    if dataset.frequency_min_hz <= 0 or dataset.frequency_min_hz >= dataset.frequency_max_hz:
        raise ValueError("Invalid frequency range")
    if not 0 < dataset.torque_headroom < runtime.torque_per_ctrl:
        raise ValueError("Torque headroom must be positive and below the actuator limit")
    if dataset.train_trajectories < 10:
        raise ValueError("At least 10 training trajectories are required")
    if dataset.train_trajectories * 30 % 100 != 0:
        raise ValueError("Training trajectory count must provide an exact 30% budget")
    _ = dataset.samples_per_trajectory
    return config
