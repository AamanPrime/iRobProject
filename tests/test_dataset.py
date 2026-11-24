from __future__ import annotations

from dataclasses import replace

import pytest

from reacher_id.dataset import generate_dataset, load_dataset
from reacher_id.validation import validate_dataset


@pytest.mark.integration
def test_small_dataset_round_trip_and_validation(phase1_config, tmp_path):
    small_dataset = replace(
        phase1_config.dataset,
        train_trajectories=10,
        validation_trajectories=2,
        id_test_trajectories=2,
        shoulder_ood_trajectories=1,
        wrist_ood_trajectories=1,
    )
    config = replace(
        phase1_config,
        dataset=small_dataset,
        validation=replace(
            phase1_config.validation,
            dataset_recheck_samples=32,
            random_state_samples=64,
        ),
    )
    metadata = generate_dataset(config, tmp_path, overwrite=False)
    arrays = load_dataset(tmp_path / "reacher_inverse_dynamics.npz")
    assert arrays["q"].shape == (16 * small_dataset.samples_per_trajectory, 2)
    assert metadata["quality"]["all_rows_feasible"]
    report = validate_dataset(config, tmp_path)
    assert report["all_rows_feasible"]
    assert report["budgets_nested"]


def test_dataset_refuses_accidental_overwrite(phase1_config, tmp_path):
    small_dataset = replace(
        phase1_config.dataset,
        train_trajectories=10,
        validation_trajectories=0,
        id_test_trajectories=0,
        shoulder_ood_trajectories=0,
        wrist_ood_trajectories=0,
    )
    config = replace(phase1_config, dataset=small_dataset)
    generate_dataset(config, tmp_path)
    with pytest.raises(FileExistsError):
        generate_dataset(config, tmp_path)
