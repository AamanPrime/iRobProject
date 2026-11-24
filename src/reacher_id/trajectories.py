"""Deterministic, analytically differentiable trajectory generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .config import Phase1Config
from .dynamics import closed_form_inverse

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class TrajectorySpec:
    trajectory_id: str
    split: str
    regime: str
    seed: int
    offset: FloatArray
    amplitudes: FloatArray
    frequencies_hz: FloatArray
    phases: FloatArray

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "split": self.split,
            "regime": self.regime,
            "seed": self.seed,
            "offset": self.offset.tolist(),
            "amplitudes": self.amplitudes.tolist(),
            "frequencies_hz": self.frequencies_hz.tolist(),
            "phases": self.phases.tolist(),
        }


@dataclass(frozen=True)
class Trajectory:
    spec: TrajectorySpec
    time: FloatArray
    q: FloatArray
    q_dot: FloatArray
    q_ddot: FloatArray

    def summary(self) -> dict[str, Any]:
        torque = closed_form_inverse(self.q, self.q_dot, self.q_ddot)
        return {
            **self.spec.to_dict(),
            "samples": int(self.time.size),
            "q_min": self.q.min(axis=0).tolist(),
            "q_max": self.q.max(axis=0).tolist(),
            "max_abs_velocity": np.max(np.abs(self.q_dot), axis=0).tolist(),
            "max_abs_acceleration": np.max(np.abs(self.q_ddot), axis=0).tolist(),
            "max_abs_closed_form_torque": np.max(np.abs(torque), axis=0).tolist(),
        }


def evaluate_spec(spec: TrajectorySpec, time: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Evaluate position and its exact first two time derivatives."""
    angular_frequency = 2.0 * np.pi * spec.frequencies_hz
    angle = time[:, None, None] * angular_frequency[None, :, :] + spec.phases[None, :, :]
    sine = np.sin(angle)
    cosine = np.cos(angle)
    q = spec.offset[None, :] + np.sum(spec.amplitudes[None, :, :] * sine, axis=-1)
    q_dot = np.sum(
        spec.amplitudes[None, :, :] * angular_frequency[None, :, :] * cosine,
        axis=-1,
    )
    q_ddot = -np.sum(
        spec.amplitudes[None, :, :] * angular_frequency[None, :, :] ** 2 * sine,
        axis=-1,
    )
    return q, q_dot, q_ddot


class TrajectoryFactory:
    """Generate bounded multi-sine trajectories with exact derivatives."""

    def __init__(self, config: Phase1Config):
        self.config = config
        dataset = config.dataset
        self.time = np.arange(dataset.samples_per_trajectory, dtype=np.float64) * dataset.sample_timestep

    def _regime_parameters(
        self,
        regime: str,
        rng: np.random.Generator,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Return local q bounds, offset, and total-amplitude ranges."""
        if regime == "id":
            q_low = np.array([-1.5, -1.2], dtype=np.float64)
            q_high = np.array([1.5, 1.2], dtype=np.float64)
            offset = rng.uniform([-0.20, -0.15], [0.20, 0.15])
            amplitude_low = np.array([0.40, 0.35])
            amplitude_high = np.array([1.10, 0.90])
        elif regime == "shoulder_ood":
            sign = float(rng.choice([-1.0, 1.0]))
            q_low = np.array([1.65, -1.2], dtype=np.float64)
            q_high = np.array([2.70, 1.2], dtype=np.float64)
            offset = np.array([rng.uniform(2.05, 2.30), rng.uniform(-0.15, 0.15)])
            if sign < 0:
                q_low[0], q_high[0] = -q_high[0], -q_low[0]
                offset[0] *= -1.0
            amplitude_low = np.array([0.18, 0.35])
            amplitude_high = np.array([0.38, 0.85])
        elif regime == "wrist_ood":
            sign = float(rng.choice([-1.0, 1.0]))
            q_low = np.array([-1.5, 1.55], dtype=np.float64)
            q_high = np.array([1.5, 2.25], dtype=np.float64)
            offset = np.array([rng.uniform(-0.20, 0.20), rng.uniform(1.82, 1.98)])
            if sign < 0:
                q_low[1], q_high[1] = -q_high[1], -q_low[1]
                offset[1] *= -1.0
            amplitude_low = np.array([0.40, 0.12])
            amplitude_high = np.array([1.05, 0.28])
        else:
            raise ValueError(f"Unknown regime: {regime}")
        return q_low, q_high, offset, np.stack([amplitude_low, amplitude_high])

    def _candidate(
        self,
        trajectory_id: str,
        split: str,
        regime: str,
        seed: int,
    ) -> Trajectory:
        rng = np.random.default_rng(seed)
        dataset = self.config.dataset
        q_low, q_high, offset, amplitude_range = self._regime_parameters(regime, rng)
        components = dataset.fourier_components

        frequencies_hz = rng.uniform(
            dataset.frequency_min_hz,
            dataset.frequency_max_hz,
            size=(2, components),
        )
        frequencies_hz.sort(axis=1)
        phases = rng.uniform(0.0, 2.0 * np.pi, size=(2, components))
        total_amplitude = rng.uniform(amplitude_range[0], amplitude_range[1])
        weights = np.stack([rng.dirichlet(np.full(components, 1.5)) for _ in range(2)])
        amplitudes = total_amplitude[:, None] * weights

        provisional = TrajectorySpec(
            trajectory_id=trajectory_id,
            split=split,
            regime=regime,
            seed=seed,
            offset=offset,
            amplitudes=amplitudes,
            frequencies_hz=frequencies_hz,
            phases=phases,
        )
        q, q_dot, q_ddot = evaluate_spec(provisional, self.time)

        # Uniformly scale each joint's sine amplitudes to satisfy every bound.
        for joint in range(2):
            deviation = q[:, joint] - offset[joint]
            ratios = [1.0]
            max_deviation = float(np.max(deviation))
            min_deviation = float(np.min(deviation))
            if max_deviation > 0:
                ratios.append((q_high[joint] - offset[joint]) / max_deviation)
            if min_deviation < 0:
                ratios.append((offset[joint] - q_low[joint]) / -min_deviation)
            max_velocity = float(np.max(np.abs(q_dot[:, joint])))
            max_acceleration = float(np.max(np.abs(q_ddot[:, joint])))
            if max_velocity > 0:
                ratios.append(self.config.envelope(regime).max_abs_velocity[joint] / max_velocity)
            if max_acceleration > 0:
                ratios.append(self.config.envelope(regime).max_abs_acceleration[joint] / max_acceleration)
            scale = min(ratios)
            if scale < 1.0:
                amplitudes[joint] *= 0.97 * scale

        spec = TrajectorySpec(
            trajectory_id=trajectory_id,
            split=split,
            regime=regime,
            seed=seed,
            offset=offset,
            amplitudes=amplitudes,
            frequencies_hz=frequencies_hz,
            phases=phases,
        )
        q, q_dot, q_ddot = evaluate_spec(spec, self.time)
        return Trajectory(spec=spec, time=self.time.copy(), q=q, q_dot=q_dot, q_ddot=q_ddot)

    def _valid(self, trajectory: Trajectory) -> bool:
        envelope = self.config.envelope(trajectory.spec.regime)
        tolerance = 1e-12
        if np.any(trajectory.q < envelope.q_low - tolerance):
            return False
        if np.any(trajectory.q > envelope.q_high + tolerance):
            return False
        if np.any(np.max(np.abs(trajectory.q_dot), axis=0) > envelope.max_abs_velocity + tolerance):
            return False
        if np.any(np.max(np.abs(trajectory.q_ddot), axis=0) > envelope.max_abs_acceleration + tolerance):
            return False
        if envelope.outside_joint is not None:
            joint = envelope.outside_joint
            if np.any(np.abs(trajectory.q[:, joint]) < float(envelope.outside_abs_min) - tolerance):
                return False

        minimum_span = {
            "id": np.array([0.25, 0.20]),
            "shoulder_ood": np.array([0.10, 0.20]),
            "wrist_ood": np.array([0.25, 0.08]),
        }[trajectory.spec.regime]
        if np.any(np.ptp(trajectory.q, axis=0) < minimum_span):
            return False
        if np.any(np.sqrt(np.mean(trajectory.q_dot**2, axis=0)) < 0.03):
            return False

        torque = closed_form_inverse(trajectory.q, trajectory.q_dot, trajectory.q_ddot)
        if np.any(np.abs(torque) > self.config.dataset.torque_headroom + tolerance):
            return False
        return True

    def generate(self, trajectory_id: str, split: str, regime: str, seed: int) -> Trajectory:
        seed_rng = np.random.default_rng(seed)
        for _ in range(self.config.dataset.max_generation_attempts):
            candidate_seed = int(seed_rng.integers(0, np.iinfo(np.int64).max, dtype=np.int64))
            trajectory = self._candidate(trajectory_id, split, regime, candidate_seed)
            if self._valid(trajectory):
                return trajectory
        raise RuntimeError(
            f"Failed to generate {regime} trajectory {trajectory_id} after "
            f"{self.config.dataset.max_generation_attempts} attempts"
        )

    def collection(self) -> list[Trajectory]:
        """Generate every configured split using deterministic per-trajectory seeds."""
        root_rng = np.random.default_rng(self.config.dataset.trajectory_seed)
        plan = (
            ("train", "id", self.config.dataset.train_trajectories),
            ("validation", "id", self.config.dataset.validation_trajectories),
            ("id_test", "id", self.config.dataset.id_test_trajectories),
            ("ood_test", "shoulder_ood", self.config.dataset.shoulder_ood_trajectories),
            ("ood_test", "wrist_ood", self.config.dataset.wrist_ood_trajectories),
        )
        trajectories: list[Trajectory] = []
        for split, regime, count in plan:
            prefix = split if regime == "id" else regime
            for index in range(count):
                seed = int(root_rng.integers(0, np.iinfo(np.int64).max, dtype=np.int64))
                trajectory_id = f"{prefix}_{index:03d}"
                trajectories.append(self.generate(trajectory_id, split, regime, seed))
        return trajectories
