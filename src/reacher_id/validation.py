"""Phase 1 acceptance checks for physics, trajectories, and serialized data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .config import Phase1Config
from .dataset import (
    atomic_write_json,
    content_sha256,
    load_dataset,
    normalization_for_budget,
)
from .dynamics import (
    MujocoDynamics,
    closed_form_bias,
    closed_form_forward,
    closed_form_inverse,
    closed_form_mass_matrix,
    closed_form_passive_force,
    ctrl_to_torque,
)
from .environment import assert_runtime, inspect_runtime
from .trajectories import TrajectorySpec, evaluate_spec


def _maximum_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))


def _assert_close(
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    atol: float,
    rtol: float,
    label: str,
) -> float:
    error = _maximum_error(actual, expected)
    if not np.allclose(actual, expected, atol=atol, rtol=rtol):
        raise AssertionError(f"{label} mismatch; maximum absolute error={error:.3e}")
    return error


def validate_dynamics(config: Phase1Config) -> dict[str, Any]:
    """Cross-check every dynamics space against an independent closed form."""
    validation = config.validation
    rng = np.random.default_rng(validation.seed)
    count = validation.random_state_samples
    q = np.column_stack(
        [
            rng.uniform(-np.pi, np.pi, count),
            rng.uniform(-2.3, 2.3, count),
        ]
    )
    q_dot = rng.uniform(-2.0, 2.0, size=(count, 2))
    q_ddot = rng.uniform(-8.0, 8.0, size=(count, 2))

    oracle = MujocoDynamics.from_suite(config.runtime.seed)
    inverse = oracle.inverse_batch(q, q_dot, q_ddot)
    analytic_mass = closed_form_mass_matrix(q)
    analytic_bias = closed_form_bias(q, q_dot)
    analytic_passive = closed_form_passive_force(q_dot)
    analytic_torque = closed_form_inverse(q, q_dot, q_ddot)
    atol, rtol = validation.absolute_tolerance, validation.relative_tolerance

    errors = {
        "mass_matrix": _assert_close(
            inverse["mass_matrix"], analytic_mass, atol=atol, rtol=rtol, label="mass matrix"
        ),
        "bias_force": _assert_close(
            inverse["qfrc_bias"], analytic_bias, atol=atol, rtol=rtol, label="bias force"
        ),
        "passive_force": _assert_close(
            inverse["qfrc_passive"], analytic_passive, atol=atol, rtol=rtol, label="passive force"
        ),
        "inverse_torque": _assert_close(
            inverse["tau_joint"], analytic_torque, atol=atol, rtol=rtol, label="inverse torque"
        ),
    }
    if np.any(inverse["nefc"] != 0):
        raise AssertionError("Interior random states unexpectedly activated constraints")
    if np.max(np.abs(inverse["qfrc_constraint"])) > config.dataset.constraint_tolerance:
        raise AssertionError("Interior random states contain constraint force")

    residual = (
        np.einsum("nij,nj->ni", inverse["mass_matrix"], q_ddot)
        + inverse["qfrc_bias"]
        - inverse["qfrc_passive"]
        - inverse["qfrc_constraint"]
        - inverse["tau_joint"]
    )
    errors["equation_residual"] = float(np.max(np.abs(residual)))
    if errors["equation_residual"] > atol:
        raise AssertionError("MuJoCo inverse-dynamics residual exceeds tolerance")

    forward_count = min(128, count)
    control = rng.uniform(-0.9, 0.9, size=(forward_count, 2))
    action_mapping_error = 0.0
    forward_acceleration_error = 0.0
    forward_inverse_error = 0.0
    for index in range(forward_count):
        forward = oracle.forward(q[index], q_dot[index], control[index])
        expected_torque = ctrl_to_torque(control[index], config.runtime.torque_per_ctrl)
        _assert_close(
            forward.tau_joint,
            expected_torque,
            atol=atol,
            rtol=rtol,
            label="action mapping",
        )
        action_mapping_error = max(
            action_mapping_error,
            _maximum_error(forward.tau_joint, expected_torque),
        )
        expected_acceleration = closed_form_forward(q[index], q_dot[index], expected_torque)
        _assert_close(
            forward.q_ddot,
            expected_acceleration,
            atol=atol,
            rtol=rtol,
            label="forward acceleration",
        )
        forward_acceleration_error = max(
            forward_acceleration_error,
            _maximum_error(forward.q_ddot, expected_acceleration),
        )
        inverse_sample = oracle.inverse(q[index], q_dot[index], forward.q_ddot)
        _assert_close(
            inverse_sample.tau_joint,
            forward.tau_joint,
            atol=atol,
            rtol=rtol,
            label="forward/inverse consistency",
        )
        forward_inverse_error = max(
            forward_inverse_error,
            _maximum_error(inverse_sample.tau_joint, forward.tau_joint),
        )
    errors.update(
        {
            "action_mapping": action_mapping_error,
            "forward_acceleration": forward_acceleration_error,
            "forward_inverse_consistency": forward_inverse_error,
        }
    )

    eigenvalues = np.linalg.eigvalsh(analytic_mass)
    condition_numbers = np.linalg.cond(analytic_mass)
    if np.min(eigenvalues) <= 0:
        raise AssertionError("Analytical mass matrix is not positive definite")

    # Ensure returned samples own their data rather than aliasing mutable mjData views.
    first = oracle.inverse(q[0], q_dot[0], q_ddot[0])
    preserved = first.tau_joint.copy()
    oracle.inverse(q[1], q_dot[1], q_ddot[1])
    if not np.array_equal(first.tau_joint, preserved):
        raise AssertionError("InverseSample aliases mutable MuJoCo memory")

    return {
        "samples": count,
        "maximum_absolute_errors": errors,
        "minimum_mass_eigenvalue": float(np.min(eigenvalues)),
        "maximum_mass_eigenvalue": float(np.max(eigenvalues)),
        "maximum_mass_condition_number": float(np.max(condition_numbers)),
        "returned_arrays_are_copies": True,
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _assert_pairwise_disjoint(groups: Mapping[str, list[str]]) -> None:
    names = list(groups)
    for index, first in enumerate(names):
        for second in names[index + 1 :]:
            overlap = set(groups[first]) & set(groups[second])
            if overlap:
                raise AssertionError(f"Split leakage between {first} and {second}: {sorted(overlap)}")


def _trajectory_from_json(raw: dict[str, Any]) -> TrajectorySpec:
    return TrajectorySpec(
        trajectory_id=raw["trajectory_id"],
        split=raw["split"],
        regime=raw["regime"],
        seed=int(raw["seed"]),
        offset=np.asarray(raw["offset"], dtype=np.float64),
        amplitudes=np.asarray(raw["amplitudes"], dtype=np.float64),
        frequencies_hz=np.asarray(raw["frequencies_hz"], dtype=np.float64),
        phases=np.asarray(raw["phases"], dtype=np.float64),
    )


def validate_dataset(config: Phase1Config, dataset_dir: str | Path) -> dict[str, Any]:
    """Validate serialization, split integrity, labels, envelopes, and normalizers."""
    directory = Path(dataset_dir).expanduser().resolve()
    arrays = load_dataset(directory / "reacher_inverse_dynamics.npz")
    metadata = _load_json(directory / "metadata.json")
    split_manifest = _load_json(directory / "split_manifest.json")
    budget_manifest = _load_json(directory / "budget_manifest.json")
    trajectory_manifest = _load_json(directory / "trajectory_manifest.json")

    expected_trajectories = config.dataset.total_trajectories
    expected_samples = expected_trajectories * config.dataset.samples_per_trajectory
    if arrays["time"].shape != (expected_samples,):
        raise AssertionError("Dataset sample count does not match configuration")
    unique_ids = set(arrays["trajectory_id"].tolist())
    if len(unique_ids) != expected_trajectories:
        raise AssertionError("Dataset trajectory count does not match configuration")
    _assert_pairwise_disjoint(split_manifest)
    if set.union(*(set(values) for values in split_manifest.values())) != unique_ids:
        raise AssertionError("Split manifest does not cover the serialized trajectories exactly")

    expected_split_counts = {
        "train": config.dataset.train_trajectories,
        "validation": config.dataset.validation_trajectories,
        "id_test": config.dataset.id_test_trajectories,
        "ood_test": config.dataset.shoulder_ood_trajectories + config.dataset.wrist_ood_trajectories,
    }
    observed_split_counts = {key: len(value) for key, value in split_manifest.items()}
    if observed_split_counts != expected_split_counts:
        raise AssertionError(f"Incorrect split counts: {observed_split_counts}")

    budgets = budget_manifest["budgets"]
    if not set(budgets["10"]) < set(budgets["30"]):
        raise AssertionError("10% trajectory budget is not a strict subset of 30%")
    if not set(budgets["30"]) < set(budgets["100"]):
        raise AssertionError("30% trajectory budget is not a strict subset of 100%")
    if set(budgets["100"]) != set(split_manifest["train"]):
        raise AssertionError("100% budget does not equal the complete training split")
    expected_budget_counts = {
        "10": config.dataset.train_trajectories * 10 // 100,
        "30": config.dataset.train_trajectories * 30 // 100,
        "100": config.dataset.train_trajectories,
    }
    if {key: len(value) for key, value in budgets.items()} != expected_budget_counts:
        raise AssertionError("Budget trajectory counts are incorrect")

    numeric_fields = (
        "time",
        "q",
        "q_dot",
        "q_ddot",
        "tau_joint",
        "qfrc_bias",
        "qfrc_passive",
        "qfrc_constraint",
        "mass_matrix",
    )
    for field in numeric_fields:
        if not np.all(np.isfinite(arrays[field])):
            raise AssertionError(f"Dataset field {field} contains non-finite values")
    if not np.all(arrays["feasible"]):
        raise AssertionError("Dataset contains rows not marked feasible")
    if np.any(arrays["nefc"] != 0):
        raise AssertionError("Primary dataset contains active constraints")
    if np.max(np.abs(arrays["qfrc_constraint"])) > config.dataset.constraint_tolerance:
        raise AssertionError("Primary dataset contains constraint force")
    if np.max(np.abs(arrays["tau_joint"])) > config.dataset.torque_headroom + 1e-12:
        raise AssertionError("Dataset exceeds torque headroom")

    # Validate regime-specific state envelopes.
    for regime in ("id", "shoulder_ood", "wrist_ood"):
        mask = arrays["regime"] == regime
        envelope = config.envelope(regime)
        q = arrays["q"][mask]
        q_dot = arrays["q_dot"][mask]
        q_ddot = arrays["q_ddot"][mask]
        if np.any(q < envelope.q_low - 1e-12) or np.any(q > envelope.q_high + 1e-12):
            raise AssertionError(f"{regime} positions exceed their envelope")
        if np.any(np.abs(q_dot) > envelope.max_abs_velocity + 1e-12):
            raise AssertionError(f"{regime} velocities exceed their envelope")
        if np.any(np.abs(q_ddot) > envelope.max_abs_acceleration + 1e-12):
            raise AssertionError(f"{regime} accelerations exceed their envelope")
        if envelope.outside_joint is not None:
            if np.any(np.abs(q[:, envelope.outside_joint]) < float(envelope.outside_abs_min) - 1e-12):
                raise AssertionError(f"{regime} contains points inside the training angle range")

    atol, rtol = config.validation.absolute_tolerance, config.validation.relative_tolerance
    analytic_torque = closed_form_inverse(arrays["q"], arrays["q_dot"], arrays["q_ddot"])
    analytic_mass = closed_form_mass_matrix(arrays["q"])
    analytic_bias = closed_form_bias(arrays["q"], arrays["q_dot"])
    analytic_passive = closed_form_passive_force(arrays["q_dot"])
    analytic_errors = {
        "torque": _assert_close(
            arrays["tau_joint"], analytic_torque, atol=atol, rtol=rtol, label="dataset torque"
        ),
        "mass_matrix": _assert_close(
            arrays["mass_matrix"], analytic_mass, atol=atol, rtol=rtol, label="dataset mass matrix"
        ),
        "bias": _assert_close(
            arrays["qfrc_bias"], analytic_bias, atol=atol, rtol=rtol, label="dataset bias"
        ),
        "passive": _assert_close(
            arrays["qfrc_passive"], analytic_passive, atol=atol, rtol=rtol, label="dataset passive force"
        ),
    }

    # Re-evaluate every stored analytical trajectory from its serialized coefficients.
    expected_time = np.arange(config.dataset.samples_per_trajectory) * config.dataset.sample_timestep
    temporal_errors = {"q": 0.0, "q_dot": 0.0, "q_ddot": 0.0, "time": 0.0}
    for raw_spec in trajectory_manifest:
        spec = _trajectory_from_json(raw_spec)
        mask = arrays["trajectory_id"] == spec.trajectory_id
        order = np.argsort(arrays["sample_index"][mask])
        stored_time = arrays["time"][mask][order]
        temporal_errors["time"] = max(
            temporal_errors["time"], _maximum_error(stored_time, expected_time)
        )
        q, q_dot, q_ddot = evaluate_spec(spec, stored_time)
        for name, expected in (("q", q), ("q_dot", q_dot), ("q_ddot", q_ddot)):
            temporal_errors[name] = max(
                temporal_errors[name], _maximum_error(arrays[name][mask][order], expected)
            )
    if any(error > atol for error in temporal_errors.values()):
        raise AssertionError(f"Serialized trajectory alignment failed: {temporal_errors}")

    # Re-query native MuJoCo for a deterministic random subset of serialized rows.
    rng = np.random.default_rng(config.validation.seed + 1)
    recheck_count = min(config.validation.dataset_recheck_samples, expected_samples)
    indices = rng.choice(expected_samples, size=recheck_count, replace=False)
    rechecked = MujocoDynamics.from_suite(config.runtime.seed).inverse_batch(
        arrays["q"][indices], arrays["q_dot"][indices], arrays["q_ddot"][indices]
    )
    native_recheck_error = _assert_close(
        arrays["tau_joint"][indices],
        rechecked["tau_joint"],
        atol=atol,
        rtol=rtol,
        label="native dataset torque recheck",
    )

    # Verify stored normalizers use only the exact budget rows.
    normalization_errors: dict[str, float] = {}
    for budget, ids in budgets.items():
        stored = _load_json(directory / f"normalization_{budget}.json")
        recomputed = normalization_for_budget(arrays, ids)
        maximum = 0.0
        for field in ("angle_features", "q", "q_dot", "q_ddot", "tau_joint"):
            for statistic in ("mean", "std", "minimum", "maximum"):
                maximum = max(
                    maximum,
                    _maximum_error(stored[field][statistic], recomputed[field][statistic]),
                )
        if maximum > atol:
            raise AssertionError(f"Normalizer mismatch for {budget}% budget")
        if stored["sample_count"] != len(ids) * config.dataset.samples_per_trajectory:
            raise AssertionError(f"Normalizer sample count is wrong for {budget}% budget")
        normalization_errors[budget] = maximum

    observed_hash = content_sha256(arrays)
    if observed_hash != metadata["dataset_content_sha256"]:
        raise AssertionError("Dataset content hash does not match metadata")

    return {
        "samples": expected_samples,
        "trajectories": expected_trajectories,
        "split_counts": observed_split_counts,
        "budget_counts": expected_budget_counts,
        "dataset_content_sha256": observed_hash,
        "maximum_absolute_errors": {
            "analytical_labels": analytic_errors,
            "temporal_alignment": temporal_errors,
            "native_torque_recheck": native_recheck_error,
            "normalization": normalization_errors,
        },
        "maximum_abs_torque": np.max(np.abs(arrays["tau_joint"]), axis=0).tolist(),
        "maximum_abs_constraint_force": float(np.max(np.abs(arrays["qfrc_constraint"]))),
        "all_rows_feasible": bool(np.all(arrays["feasible"])),
        "split_ids_pairwise_disjoint": True,
        "budgets_nested": True,
    }


def run_phase1_validation(
    config: Phase1Config,
    dataset_dir: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    runtime = inspect_runtime(config.runtime.seed)
    assert_runtime(runtime, config.runtime)
    report = {
        "status": "passed",
        "runtime": runtime.to_dict(),
        "dynamics": validate_dynamics(config),
        "dataset": validate_dataset(config, dataset_dir),
    }
    if output_path is not None:
        atomic_write_json(Path(output_path).expanduser().resolve(), report)
    return report
