from __future__ import annotations

import numpy as np

from reacher_id.dynamics import closed_form_inverse
from reacher_id.trajectories import TrajectoryFactory, evaluate_spec


def test_generated_trajectories_obey_each_regime(phase1_config):
    factory = TrajectoryFactory(phase1_config)
    for index, regime in enumerate(("id", "shoulder_ood", "wrist_ood")):
        trajectory = factory.generate(f"test_{regime}", "test", regime, 1000 + index)
        envelope = phase1_config.envelope(regime)
        assert np.all(trajectory.q >= envelope.q_low - 1e-12)
        assert np.all(trajectory.q <= envelope.q_high + 1e-12)
        assert np.all(np.abs(trajectory.q_dot) <= envelope.max_abs_velocity + 1e-12)
        assert np.all(np.abs(trajectory.q_ddot) <= envelope.max_abs_acceleration + 1e-12)
        if envelope.outside_joint is not None:
            assert np.all(
                np.abs(trajectory.q[:, envelope.outside_joint])
                >= float(envelope.outside_abs_min) - 1e-12
            )
        torque = closed_form_inverse(trajectory.q, trajectory.q_dot, trajectory.q_ddot)
        assert np.max(np.abs(torque)) <= phase1_config.dataset.torque_headroom + 1e-12


def test_serialized_spec_reproduces_exact_derivatives(phase1_config):
    factory = TrajectoryFactory(phase1_config)
    trajectory = factory.generate("repeatable", "test", "id", 12345)
    q, q_dot, q_ddot = evaluate_spec(trajectory.spec, trajectory.time)
    assert np.array_equal(q, trajectory.q)
    assert np.array_equal(q_dot, trajectory.q_dot)
    assert np.array_equal(q_ddot, trajectory.q_ddot)


def test_trajectory_generation_is_deterministic(phase1_config):
    factory = TrajectoryFactory(phase1_config)
    first = factory.generate("same", "test", "id", 9988)
    second = factory.generate("same", "test", "id", 9988)
    assert first.spec.to_dict() == second.spec.to_dict()
    assert np.array_equal(first.q, second.q)
