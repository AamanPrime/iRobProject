"""MuJoCo oracle and independent closed-form reacher dynamics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mujoco
import numpy as np
from numpy.typing import ArrayLike, NDArray

from .environment import load_reacher

FloatArray = NDArray[np.float64]

# Compiler-derived constants for dm-control 1.0.52 / MuJoCo 4.0.1.
A_INERTIA = 9.7581009413152562e-4
B_COUPLING = 2.7394687939302998e-4
D_INERTIA = 1.8867358279909104e-4
JOINT_DAMPING = 0.01
TORQUE_PER_CTRL = 0.05


def _state_vector(value: ArrayLike, name: str) -> FloatArray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (2,):
        raise ValueError(f"{name} must have shape (2,), got {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains a non-finite value")
    return array


def ctrl_to_torque(ctrl: ArrayLike, torque_per_ctrl: float = TORQUE_PER_CTRL) -> FloatArray:
    return _state_vector(ctrl, "ctrl") * torque_per_ctrl


def torque_to_ctrl(
    torque: ArrayLike,
    torque_per_ctrl: float = TORQUE_PER_CTRL,
    *,
    clip: bool = False,
) -> FloatArray:
    ctrl = _state_vector(torque, "torque") / torque_per_ctrl
    return np.clip(ctrl, -1.0, 1.0) if clip else ctrl


def closed_form_mass_matrix(q: ArrayLike) -> FloatArray:
    q_array = np.asarray(q, dtype=np.float64)
    if q_array.shape[-1:] != (2,):
        raise ValueError("q must end in dimension 2")
    cosine = np.cos(q_array[..., 1])
    output = np.empty(q_array.shape[:-1] + (2, 2), dtype=np.float64)
    output[..., 0, 0] = A_INERTIA + 2.0 * B_COUPLING * cosine
    output[..., 0, 1] = D_INERTIA + B_COUPLING * cosine
    output[..., 1, 0] = output[..., 0, 1]
    output[..., 1, 1] = D_INERTIA
    return output


def closed_form_bias(q: ArrayLike, q_dot: ArrayLike) -> FloatArray:
    q_array = np.asarray(q, dtype=np.float64)
    velocity = np.asarray(q_dot, dtype=np.float64)
    if q_array.shape != velocity.shape or q_array.shape[-1:] != (2,):
        raise ValueError("q and q_dot must have matching shapes ending in 2")
    sine = np.sin(q_array[..., 1])
    dq1, dq2 = velocity[..., 0], velocity[..., 1]
    output = np.empty_like(velocity)
    output[..., 0] = -B_COUPLING * sine * (2.0 * dq1 * dq2 + dq2**2)
    output[..., 1] = B_COUPLING * sine * dq1**2
    return output


def closed_form_passive_force(q_dot: ArrayLike) -> FloatArray:
    return -JOINT_DAMPING * np.asarray(q_dot, dtype=np.float64)


def closed_form_inverse(q: ArrayLike, q_dot: ArrayLike, q_ddot: ArrayLike) -> FloatArray:
    q_array = np.asarray(q, dtype=np.float64)
    velocity = np.asarray(q_dot, dtype=np.float64)
    acceleration = np.asarray(q_ddot, dtype=np.float64)
    if q_array.shape != velocity.shape or q_array.shape != acceleration.shape:
        raise ValueError("q, q_dot, and q_ddot must have matching shapes")
    mass = closed_form_mass_matrix(q_array)
    inertial = np.einsum("...ij,...j->...i", mass, acceleration)
    return inertial + closed_form_bias(q_array, velocity) + JOINT_DAMPING * velocity


def closed_form_forward(q: ArrayLike, q_dot: ArrayLike, torque: ArrayLike) -> FloatArray:
    q_array = np.asarray(q, dtype=np.float64)
    velocity = np.asarray(q_dot, dtype=np.float64)
    torque_array = np.asarray(torque, dtype=np.float64)
    if q_array.shape != velocity.shape or q_array.shape != torque_array.shape:
        raise ValueError("q, q_dot, and torque must have matching shapes")
    right_hand_side = torque_array - closed_form_bias(q_array, velocity) - JOINT_DAMPING * velocity
    return np.linalg.solve(closed_form_mass_matrix(q_array), right_hand_side)


@dataclass(frozen=True)
class InverseSample:
    q: FloatArray
    q_dot: FloatArray
    q_ddot: FloatArray
    tau_joint: FloatArray
    qfrc_bias: FloatArray
    qfrc_passive: FloatArray
    qfrc_constraint: FloatArray
    mass_matrix: FloatArray
    nefc: int


@dataclass(frozen=True)
class ForwardSample:
    q: FloatArray
    q_dot: FloatArray
    q_ddot: FloatArray
    ctrl: FloatArray
    tau_joint: FloatArray
    qfrc_bias: FloatArray
    qfrc_passive: FloatArray
    qfrc_constraint: FloatArray
    mass_matrix: FloatArray
    nefc: int


class MujocoDynamics:
    """A private MuJoCo data object used as a synchronized dynamics oracle."""

    def __init__(self, physics: Any):
        self.physics = physics.copy(share_model=True)
        self.model = self.physics.model
        self.data = self.physics.data
        if (self.model.nq, self.model.nv, self.model.nu) != (2, 2, 2):
            raise ValueError("MujocoDynamics currently supports the pinned 2-DoF reacher only")

    @classmethod
    def from_suite(cls, seed: int = 0) -> "MujocoDynamics":
        return cls(load_reacher(seed).physics)

    def dense_mass_matrix(self) -> FloatArray:
        matrix = np.empty((self.model.nv, self.model.nv), dtype=np.float64)
        mujoco.mj_fullM(self.model.ptr, self.data.ptr, matrix)
        return matrix

    def _set_common_state(self, q: ArrayLike, q_dot: ArrayLike) -> tuple[FloatArray, FloatArray]:
        q_array = _state_vector(q, "q")
        velocity = _state_vector(q_dot, "q_dot")
        self.data.qpos[:] = q_array
        self.data.qvel[:] = velocity
        self.data.ctrl[:] = 0.0
        self.data.qfrc_applied[:] = 0.0
        self.data.xfrc_applied[:] = 0.0
        if self.model.na:
            self.data.act[:] = 0.0
        return q_array, velocity

    def inverse(self, q: ArrayLike, q_dot: ArrayLike, q_ddot: ArrayLike) -> InverseSample:
        q_array, velocity = self._set_common_state(q, q_dot)
        acceleration = _state_vector(q_ddot, "q_ddot")
        self.data.qacc[:] = acceleration
        mujoco.mj_inverse(self.model.ptr, self.data.ptr)
        return InverseSample(
            q=q_array.copy(),
            q_dot=velocity.copy(),
            q_ddot=acceleration.copy(),
            tau_joint=self.data.qfrc_inverse.copy(),
            qfrc_bias=self.data.qfrc_bias.copy(),
            qfrc_passive=self.data.qfrc_passive.copy(),
            qfrc_constraint=self.data.qfrc_constraint.copy(),
            mass_matrix=self.dense_mass_matrix(),
            nefc=int(self.data.nefc),
        )

    def forward(self, q: ArrayLike, q_dot: ArrayLike, ctrl: ArrayLike) -> ForwardSample:
        q_array, velocity = self._set_common_state(q, q_dot)
        control = _state_vector(ctrl, "ctrl")
        if np.any(np.abs(control) > 1.0 + 1e-12):
            raise ValueError("ctrl exceeds the stock reacher action range")
        self.data.ctrl[:] = control
        mujoco.mj_forward(self.model.ptr, self.data.ptr)
        return ForwardSample(
            q=q_array.copy(),
            q_dot=velocity.copy(),
            q_ddot=self.data.qacc.copy(),
            ctrl=control.copy(),
            tau_joint=self.data.qfrc_actuator.copy(),
            qfrc_bias=self.data.qfrc_bias.copy(),
            qfrc_passive=self.data.qfrc_passive.copy(),
            qfrc_constraint=self.data.qfrc_constraint.copy(),
            mass_matrix=self.dense_mass_matrix(),
            nefc=int(self.data.nefc),
        )

    def inverse_batch(self, q: ArrayLike, q_dot: ArrayLike, q_ddot: ArrayLike) -> dict[str, FloatArray]:
        positions = np.asarray(q, dtype=np.float64)
        velocities = np.asarray(q_dot, dtype=np.float64)
        accelerations = np.asarray(q_ddot, dtype=np.float64)
        if positions.ndim != 2 or positions.shape[1] != 2:
            raise ValueError("Batched q must have shape (N, 2)")
        if positions.shape != velocities.shape or positions.shape != accelerations.shape:
            raise ValueError("Batched q, q_dot, and q_ddot must have identical shapes")

        count = positions.shape[0]
        output: dict[str, FloatArray] = {
            "tau_joint": np.empty((count, 2), dtype=np.float64),
            "qfrc_bias": np.empty((count, 2), dtype=np.float64),
            "qfrc_passive": np.empty((count, 2), dtype=np.float64),
            "qfrc_constraint": np.empty((count, 2), dtype=np.float64),
            "mass_matrix": np.empty((count, 2, 2), dtype=np.float64),
            "nefc": np.empty(count, dtype=np.int32),
        }
        for index in range(count):
            sample = self.inverse(positions[index], velocities[index], accelerations[index])
            output["tau_joint"][index] = sample.tau_joint
            output["qfrc_bias"][index] = sample.qfrc_bias
            output["qfrc_passive"][index] = sample.qfrc_passive
            output["qfrc_constraint"][index] = sample.qfrc_constraint
            output["mass_matrix"][index] = sample.mass_matrix
            output["nefc"][index] = sample.nefc
        return output
