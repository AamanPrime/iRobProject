"""Leakage-free Phase 1 dataset construction and artifact serialization."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from .config import Phase1Config
from .dynamics import MujocoDynamics
from .environment import assert_runtime, inspect_runtime
from .trajectories import Trajectory, TrajectoryFactory


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as file:
        json.dump(_jsonable(payload), file, indent=2, sort_keys=True)
        file.write("\n")
        temporary = Path(file.name)
    os.replace(temporary, path)


def atomic_write_npz(path: Path, arrays: Mapping[str, NDArray[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as file:
        np.savez_compressed(file, **arrays)
        temporary = Path(file.name)
    os.replace(temporary, path)


def content_sha256(arrays: Mapping[str, NDArray[Any]]) -> str:
    """Hash array names, dtypes, shapes, and bytes independently of ZIP metadata."""
    digest = hashlib.sha256()
    for key in sorted(arrays):
        array = np.ascontiguousarray(arrays[key])
        digest.update(key.encode("utf-8"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def _concatenate_trajectory_fields(trajectories: list[Trajectory]) -> dict[str, NDArray[Any]]:
    samples = sum(trajectory.time.size for trajectory in trajectories)
    trajectory_ids = np.empty(samples, dtype="U32")
    splits = np.empty(samples, dtype="U16")
    regimes = np.empty(samples, dtype="U24")
    trajectory_seeds = np.empty(samples, dtype=np.int64)
    sample_indices = np.empty(samples, dtype=np.int32)
    time = np.empty(samples, dtype=np.float64)
    q = np.empty((samples, 2), dtype=np.float64)
    q_dot = np.empty((samples, 2), dtype=np.float64)
    q_ddot = np.empty((samples, 2), dtype=np.float64)

    cursor = 0
    for trajectory in trajectories:
        count = trajectory.time.size
        selection = slice(cursor, cursor + count)
        trajectory_ids[selection] = trajectory.spec.trajectory_id
        splits[selection] = trajectory.spec.split
        regimes[selection] = trajectory.spec.regime
        trajectory_seeds[selection] = trajectory.spec.seed
        sample_indices[selection] = np.arange(count, dtype=np.int32)
        time[selection] = trajectory.time
        q[selection] = trajectory.q
        q_dot[selection] = trajectory.q_dot
        q_ddot[selection] = trajectory.q_ddot
        cursor += count

    return {
        "trajectory_id": trajectory_ids,
        "split": splits,
        "regime": regimes,
        "trajectory_seed": trajectory_seeds,
        "sample_index": sample_indices,
        "time": time,
        "q": q,
        "q_dot": q_dot,
        "q_ddot": q_ddot,
    }


def create_budget_manifest(train_ids: list[str], config: Phase1Config) -> dict[str, Any]:
    rng = np.random.default_rng(config.dataset.budget_seed)
    ordered = np.asarray(sorted(train_ids), dtype="U32")
    rng.shuffle(ordered)
    count = len(ordered)
    count_10 = count * 10 // 100
    count_30 = count * 30 // 100
    budgets = {
        "10": ordered[:count_10].tolist(),
        "30": ordered[:count_30].tolist(),
        "100": ordered.tolist(),
    }
    return {
        "budget_seed": config.dataset.budget_seed,
        "ordering": ordered.tolist(),
        "budgets": budgets,
        "trajectory_counts": {key: len(value) for key, value in budgets.items()},
        "sample_counts": {
            key: len(value) * config.dataset.samples_per_trajectory for key, value in budgets.items()
        },
    }


def _statistics(values: NDArray[np.float64]) -> dict[str, Any]:
    mean = values.mean(axis=0)
    standard_deviation = values.std(axis=0)
    standard_deviation = np.maximum(standard_deviation, 1e-12)
    return {
        "mean": mean.tolist(),
        "std": standard_deviation.tolist(),
        "minimum": values.min(axis=0).tolist(),
        "maximum": values.max(axis=0).tolist(),
    }


def normalization_for_budget(
    arrays: Mapping[str, NDArray[Any]],
    trajectory_ids: list[str],
) -> dict[str, Any]:
    mask = np.isin(arrays["trajectory_id"], np.asarray(trajectory_ids))
    if not np.any(mask):
        raise ValueError("Budget contains no dataset rows")
    q = np.asarray(arrays["q"][mask], dtype=np.float64)
    angle_features = np.concatenate([np.sin(q), np.cos(q)], axis=1)
    return {
        "trajectory_ids": trajectory_ids,
        "sample_count": int(np.count_nonzero(mask)),
        "feature_order": {
            "angle_features": ["sin_q1", "sin_q2", "cos_q1", "cos_q2"],
            "q": ["q1", "q2"],
            "q_dot": ["dq1", "dq2"],
            "q_ddot": ["ddq1", "ddq2"],
            "tau_joint": ["tau1", "tau2"],
        },
        "angle_features": _statistics(angle_features),
        "q": _statistics(q),
        "q_dot": _statistics(np.asarray(arrays["q_dot"][mask], dtype=np.float64)),
        "q_ddot": _statistics(np.asarray(arrays["q_ddot"][mask], dtype=np.float64)),
        "tau_joint": _statistics(np.asarray(arrays["tau_joint"][mask], dtype=np.float64)),
    }


def generate_dataset(
    config: Phase1Config,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate, label, verify, and serialize the complete Phase 1 dataset."""
    output = Path(output_dir).expanduser().resolve()
    dataset_path = output / "reacher_inverse_dynamics.npz"
    if dataset_path.exists() and not overwrite:
        raise FileExistsError(f"{dataset_path} already exists; pass overwrite=True to regenerate")
    output.mkdir(parents=True, exist_ok=True)

    runtime = inspect_runtime(config.runtime.seed)
    assert_runtime(runtime, config.runtime)
    trajectories = TrajectoryFactory(config).collection()
    arrays = _concatenate_trajectory_fields(trajectories)

    oracle = MujocoDynamics.from_suite(config.runtime.seed)
    labels = oracle.inverse_batch(arrays["q"], arrays["q_dot"], arrays["q_ddot"])
    arrays.update(labels)

    constraint_norm = np.max(np.abs(arrays["qfrc_constraint"]), axis=1)
    torque_norm = np.max(np.abs(arrays["tau_joint"]), axis=1)
    feasible = (
        np.all(np.isfinite(arrays["tau_joint"]), axis=1)
        & (constraint_norm <= config.dataset.constraint_tolerance)
        & (arrays["nefc"] == 0)
        & (torque_norm <= config.dataset.torque_headroom + 1e-12)
    )
    arrays["feasible"] = feasible
    if not np.all(feasible):
        bad = np.flatnonzero(~feasible)[:10]
        raise RuntimeError(f"Generated dataset contains infeasible rows at indices {bad.tolist()}")

    split_manifest: dict[str, list[str]] = {}
    for split in ("train", "validation", "id_test", "ood_test"):
        split_manifest[split] = sorted(
            {trajectory.spec.trajectory_id for trajectory in trajectories if trajectory.spec.split == split}
        )
    train_ids = split_manifest["train"]
    budget_manifest = create_budget_manifest(train_ids, config)

    atomic_write_npz(dataset_path, arrays)
    dataset_hash = content_sha256(arrays)
    atomic_write_json(output / "trajectory_manifest.json", [trajectory.summary() for trajectory in trajectories])
    atomic_write_json(output / "split_manifest.json", split_manifest)
    atomic_write_json(output / "budget_manifest.json", budget_manifest)
    for budget, ids in budget_manifest["budgets"].items():
        atomic_write_json(
            output / f"normalization_{budget}.json",
            normalization_for_budget(arrays, ids),
        )

    metadata = {
        "created_utc": datetime.now(UTC).isoformat(),
        "dataset_content_sha256": dataset_hash,
        "dataset_file": dataset_path.name,
        "runtime": runtime.to_dict(),
        "config": asdict(config),
        "array_schema": {
            key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in arrays.items()
        },
        "counts": {
            "trajectories": len(trajectories),
            "samples": int(arrays["time"].size),
            "samples_per_trajectory": config.dataset.samples_per_trajectory,
            "splits": {key: len(value) for key, value in split_manifest.items()},
            "regimes": {
                regime: sum(trajectory.spec.regime == regime for trajectory in trajectories)
                for regime in ("id", "shoulder_ood", "wrist_ood")
            },
        },
        "quality": {
            "all_rows_feasible": bool(np.all(feasible)),
            "max_abs_torque": np.max(np.abs(arrays["tau_joint"]), axis=0).tolist(),
            "max_abs_constraint_force": float(np.max(constraint_norm)),
            "max_nefc": int(np.max(arrays["nefc"])),
        },
    }
    atomic_write_json(output / "metadata.json", metadata)
    return metadata


def load_dataset(path: str | Path) -> dict[str, NDArray[Any]]:
    with np.load(Path(path), allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}
