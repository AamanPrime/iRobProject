from __future__ import annotations

import numpy as np

from reacher_id.dynamics import (
    MujocoDynamics,
    closed_form_forward,
    closed_form_inverse,
    closed_form_mass_matrix,
    ctrl_to_torque,
    torque_to_ctrl,
)


def test_control_torque_round_trip():
    ctrl = np.array([0.4, -0.6])
    torque = ctrl_to_torque(ctrl)
    assert np.allclose(torque, [0.02, -0.03])
    assert np.allclose(torque_to_ctrl(torque), ctrl)
    assert np.allclose(torque_to_ctrl([0.1, -0.1], clip=True), [1.0, -1.0])


def test_closed_form_matches_mujoco_inverse_and_mass(phase1_config):
    rng = np.random.default_rng(42)
    oracle = MujocoDynamics.from_suite(phase1_config.runtime.seed)
    for _ in range(64):
        q = np.array([rng.uniform(-np.pi, np.pi), rng.uniform(-2.3, 2.3)])
        q_dot = rng.uniform(-2.0, 2.0, 2)
        q_ddot = rng.uniform(-8.0, 8.0, 2)
        sample = oracle.inverse(q, q_dot, q_ddot)
        assert sample.nefc == 0
        assert np.allclose(sample.mass_matrix, closed_form_mass_matrix(q), atol=1e-12, rtol=1e-10)
        assert np.allclose(sample.tau_joint, closed_form_inverse(q, q_dot, q_ddot), atol=1e-12, rtol=1e-10)


def test_forward_inverse_consistency(phase1_config):
    rng = np.random.default_rng(7)
    oracle = MujocoDynamics.from_suite(phase1_config.runtime.seed)
    for _ in range(32):
        q = np.array([rng.uniform(-np.pi, np.pi), rng.uniform(-2.3, 2.3)])
        q_dot = rng.uniform(-2.0, 2.0, 2)
        ctrl = rng.uniform(-0.9, 0.9, 2)
        forward = oracle.forward(q, q_dot, ctrl)
        expected_torque = ctrl_to_torque(ctrl)
        assert np.allclose(forward.tau_joint, expected_torque, atol=1e-12, rtol=1e-10)
        assert np.allclose(
            forward.q_ddot,
            closed_form_forward(q, q_dot, expected_torque),
            atol=1e-12,
            rtol=1e-10,
        )
        inverse = oracle.inverse(q, q_dot, forward.q_ddot)
        assert np.allclose(inverse.tau_joint, forward.tau_joint, atol=1e-12, rtol=1e-10)


def test_oracle_returns_owned_copies(phase1_config):
    oracle = MujocoDynamics.from_suite(phase1_config.runtime.seed)
    first = oracle.inverse([0.1, 0.2], [0.3, -0.4], [1.0, -2.0])
    preserved = first.tau_joint.copy()
    oracle.inverse([-0.7, 1.1], [-0.2, 0.8], [-3.0, 2.0])
    assert np.array_equal(first.tau_joint, preserved)
