# Reacher inverse-dynamics requirements: source addendum

Research snapshot: **2026-11-24**. This addendum records findings that were not explicit in the earlier notes under `research_notes/Physics informed reacher inverse dynamics/`.

## 1. The required closed-loop task is not the built-in `easy` task

The official [`reacher.py` at dm_control 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py) confirms that `easy` randomizes a Cartesian target and returns observations named `position`, `to_target`, and `velocity`. It does not define a desired joint trajectory, desired acceleration, computed-torque controller, or joint-space tracking metric. The course project must therefore reuse the `reacher` plant while adding a custom joint-space tracking experiment.

The corresponding [`reacher.xml`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml) confirms:

- two hinge joints (`shoulder`, `wrist`);
- a `0.02 s` physics timestep;
- joint damping `0.01`;
- motor gear `0.05` and controls in `[-1, 1]`;
- disabled contacts;
- wrist limits of `[-160°, 160°]`.

Consequently, the stock controls are not joint torques. For this model, generalized actuator torque is `tau = 0.05 * ctrl`, so the realizable torque range is `[-0.05, 0.05] N·m` for each joint.

## 2. “LNN” needs an operational definition

Two related model classes are commonly called Lagrangian neural networks:

1. **DeLaN** learns a positive-definite configuration-dependent inertia matrix and a potential/gravity term, then obtains inverse and forward dynamics from the Euler–Lagrange structure. It was designed for robot inverse dynamics and tracking control. Source: Lutter, Ritter, and Peters, [“Deep Lagrangian Networks”](https://arxiv.org/html/1907.04490).
2. **Unrestricted LNN** learns a scalar `L(q, q_dot)` and was introduced mainly for conservative forward dynamics. It requires a velocity Hessian inversion and does not naturally model damping or motor input without an added generalized-force term. Source: Cranmer et al., [“Lagrangian Neural Networks”](https://arxiv.org/html/2003.04630).

For this project, the correct centerline is a **DeLaN-style LNN** because the required output is inverse torque and the plant is an ordinary rigid two-link manipulator. The mass matrix should be formed as `M_theta(q) = L_theta(q)L_theta(q)^T` with a strictly positive Cholesky diagonal.

## 3. A conservative Lagrangian alone is insufficient

The stock MuJoCo model has viscous joint damping. In the smooth interior its actuator torque is

`tau = M(q) q_ddot + c(q, q_dot) + 0.01 q_dot`.

The final term is dissipative and cannot be represented by an ordinary conservative Lagrangian. The structured model therefore needs an explicit learned or known dissipation term, preferably a nonnegative diagonal viscous model for this exact plant. Recent robot inverse-dynamics evidence also warns that Lagrangian models perform poorly when dissipative motor effects are silently folded into a conservative model: Trinh et al., [“Newtonian and Lagrangian Neural Networks: A Comparison Towards Efficient Inverse Dynamics Identification”](https://arxiv.org/html/2506.17994v1).

## 4. Computed torque must be distinguished from PD plus feedforward

The recommended controller is the true current-state computed-torque form:

`a_cmd = q_ddot_d + K_d(q_dot_d - q_dot) + K_p angle_error(q_d, q)`

`tau_cmd = inverse_model(q, q_dot, a_cmd)`.

This differs from evaluating inverse dynamics only at the desired state and adding a torque-space PD term. The current-state formulation is the standard feedback-linearizing interpretation of computed-torque control. See the trajectory-tracking section of Russ Tedrake’s [Manipulator Control notes](https://manipulation.csail.mit.edu/force.html#trajectory-tracking-1).

All models must use identical gains, update rate, reference trajectories, initial states, torque clipping, and MuJoCo settings.

## 5. “Two-second rollout error” is ambiguous for an inverse-only black box

A DeLaN model supplies forward dynamics naturally by solving its learned structured equation for acceleration. A generic inverse MLP, `f_inv(q, q_dot, q_ddot) -> tau`, does not.

There are three defensible choices:

1. numerically invert the inverse MLP at every rollout step;
2. recover a local inertia and bias from the inverse model, then solve for acceleration;
3. train a separate black-box forward head on the same tuples.

The author DeLaN repository uses separate black-box forward and inverse networks trained from the same `(q, q_dot, q_ddot, tau)` records: [`jax_Black_Box_model.py`](https://github.com/milutter/deep_lagrangian_networks/blob/main/deep_lagrangian_networks/jax_Black_Box_model.py). This is the clearest course-project protocol:

- use **BB-ID** for inverse-torque metrics and computed-torque control;
- use a separately named **BB-FD** for open-loop rollout comparison;
- derive both directions from the same parameters for DeLaN;
- never imply that an inverse-only MLP directly produces a forward rollout.

As a secondary diagnostic, forward dynamics can be extracted from an inverse estimator by identifying inertia and bias terms. See Dalla Libera et al., [“Forward Dynamics Estimation from Data-Driven Inverse Dynamics Learning”](https://arxiv.org/html/2307.05093v1).

## 6. Environment status

The initial virtual environment was created with **Python 3.14.4**. PyPI metadata confirms that `mujoco==4.0.1` publishes Python 3.14 wheels, but implementation testing found that `labmaze==1.0.6`—a mandatory `dm_control` dependency—does not. It falls back to a Bazel source build. The canonical implementation therefore uses **Python 3.12** in `.venv`, where the complete binary dependency set installs reproducibly. The old exact dependency pins in the DeLaN research repository remain code/equation references rather than runtime requirements.

## 7. Primary-source map

- dm_control reacher task: <https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py>
- dm_control reacher MJCF: <https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml>
- MuJoCo equations, actuation, passive forces, and integration: <https://mujoco.readthedocs.io/en/4.0.1/computation/index.html>
- DeLaN paper: <https://arxiv.org/html/1907.04490>
- LNN paper: <https://arxiv.org/html/2003.04630>
- DeLaN reference implementation: <https://github.com/milutter/deep_lagrangian_networks>
- Structured Mechanical Models: <https://proceedings.mlr.press/v120/gupta20a.html>
- computed-torque overview: <https://manipulation.csail.mit.edu/force.html#trajectory-tracking-1>
- inverse-to-forward reconstruction: <https://arxiv.org/html/2307.05093v1>
- recent inverse-dynamics/friction comparison: <https://arxiv.org/html/2506.17994v1>

## 8. Numerical feasibility audit of the proposed experiment envelope

Using the closed-form coefficients already verified against the pinned MuJoCo model, a dense `q2` sweep and exact corner evaluation over

```text
q2 in [-1.2, 1.2] rad
|q_dot_i| <= 2 rad/s
|q_ddot_i| <= 8 rad/s²
```

produced componentwise worst-case required torques of approximately `0.03667 N·m` and `0.02547 N·m`. Both are below the proposed `0.045 N·m` dataset headroom and the physical `0.05 N·m` actuator limit. Over `q2 in [-2.3,2.3]`, the analytical mass matrix remained positive definite; its worst sampled spectral condition number was approximately `37.9` at `q2=0`. These are design checks, not substitutes for runtime checks against the installed MuJoCo build.
