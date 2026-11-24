"""Pinned dm_control reacher construction and runtime inspection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from importlib import metadata
import os
import platform
import sys
from typing import Any

# Select a headless backend unless the caller explicitly requests another one.
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("LC_ALL", "C.UTF-8")

import mujoco
import numpy as np
from dm_control import suite
from dm_control.suite import reacher

from .config import RuntimeConfig


@dataclass(frozen=True)
class RuntimeInfo:
    python_version: str
    platform: str
    dm_control_version: str
    mujoco_python_version: str
    mujoco_library_version: str
    xml_sha256: str
    xml_type: str
    nq: int
    nv: int
    nu: int
    na: int
    joint_names: tuple[str, ...]
    joint_ranges: tuple[tuple[float, float], ...]
    joint_limited: tuple[bool, ...]
    action_shape: tuple[int, ...]
    action_minimum: tuple[float, ...]
    action_maximum: tuple[float, ...]
    actuator_gears: tuple[float, ...]
    observation_shapes: dict[str, tuple[int, ...]]
    physics_timestep: float
    control_timestep: float
    integrator_id: int
    integrator_name: str
    has_sparse_M: bool
    has_legacy_qM: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def model_xml_bytes() -> bytes:
    xml, _ = reacher.get_model_and_assets()
    return xml if isinstance(xml, bytes) else xml.encode("utf-8")


def load_reacher(seed: int = 0):
    """Load and reset the pinned reacher/easy environment."""
    env = suite.load("reacher", "easy", task_kwargs={"random": seed})
    env.reset()
    return env


def inspect_runtime(seed: int = 0) -> RuntimeInfo:
    env = load_reacher(seed)
    model, data = env.physics.model, env.physics.data
    action_spec = env.action_spec()
    observation = env.reset().observation

    joint_names = tuple(model.id2name(index, "joint") for index in range(model.njnt))
    joint_ranges = tuple(tuple(float(x) for x in row) for row in model.jnt_range.copy())
    joint_limited = tuple(bool(x) for x in model.jnt_limited.copy())
    actuator_gears = tuple(float(x) for x in model.actuator_gear[:, 0].copy())
    integrator_id = int(model.opt.integrator)
    try:
        integrator_name = mujoco.mjtIntegrator(integrator_id).name
    except ValueError:
        integrator_name = f"UNKNOWN_{integrator_id}"

    return RuntimeInfo(
        python_version=platform.python_version(),
        platform=f"{sys.platform}-{platform.machine()}",
        dm_control_version=metadata.version("dm-control"),
        mujoco_python_version=mujoco.__version__,
        mujoco_library_version=mujoco.mj_versionString(),
        xml_sha256=hashlib.sha256(model_xml_bytes()).hexdigest(),
        xml_type=type(reacher.get_model_and_assets()[0]).__name__,
        nq=int(model.nq),
        nv=int(model.nv),
        nu=int(model.nu),
        na=int(model.na),
        joint_names=joint_names,
        joint_ranges=joint_ranges,
        joint_limited=joint_limited,
        action_shape=tuple(action_spec.shape),
        action_minimum=tuple(float(x) for x in np.asarray(action_spec.minimum)),
        action_maximum=tuple(float(x) for x in np.asarray(action_spec.maximum)),
        actuator_gears=actuator_gears,
        observation_shapes={key: tuple(value.shape) for key, value in observation.items()},
        physics_timestep=float(env.physics.timestep()),
        control_timestep=float(env.control_timestep()),
        integrator_id=integrator_id,
        integrator_name=integrator_name,
        has_sparse_M=hasattr(data, "M"),
        has_legacy_qM=hasattr(data, "qM"),
    )


def assert_runtime(info: RuntimeInfo, expected: RuntimeConfig) -> None:
    """Fail fast if the runtime no longer matches the experiment contract."""
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(info.dm_control_version == expected.dm_control_version, "dm-control version mismatch")
    require(info.mujoco_python_version == expected.mujoco_version, "MuJoCo Python version mismatch")
    require(info.mujoco_library_version == expected.mujoco_version, "MuJoCo library version mismatch")
    require(info.xml_sha256 == expected.xml_sha256, "reacher XML hash mismatch")
    require((info.nq, info.nv, info.nu, info.na) == (2, 2, 2, 0), "unexpected model dimensions")
    require(info.joint_names == ("shoulder", "wrist"), "unexpected joint order")
    require(info.action_shape == (2,), "unexpected action shape")
    require(np.allclose(info.action_minimum, (-1.0, -1.0)), "unexpected action minimum")
    require(np.allclose(info.action_maximum, (1.0, 1.0)), "unexpected action maximum")
    require(np.allclose(info.actuator_gears, (expected.torque_per_ctrl,) * 2), "unexpected actuator gear")
    require(np.isclose(info.physics_timestep, expected.physics_timestep), "physics timestep mismatch")
    require(np.isclose(info.control_timestep, expected.control_timestep), "control timestep mismatch")
    require(info.integrator_name == "mjINT_EULER", "reacher is no longer using Euler integration")
    require(info.has_sparse_M and not info.has_legacy_qM, "unexpected MuJoCo 4 mass-matrix API")
    require(tuple(info.observation_shapes) == ("position", "to_target", "velocity"), "observation order mismatch")

    if errors:
        raise RuntimeError("Runtime contract failed:\n- " + "\n- ".join(errors))
