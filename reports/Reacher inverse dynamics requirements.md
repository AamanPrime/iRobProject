# Reacher inverse dynamics project requirements

**Research and requirements synthesis — 24 November 2026**

## Executive conclusion

This project is a **supervised inverse-dynamics learning and closed-loop robot-control study**, not a reinforcement-learning project. It uses the physical plant from `dm_control`’s `reacher/easy`, but the required joint-space trajectory-tracking task must be implemented separately because the built-in task only moves the fingertip toward a static Cartesian target.

The central comparison is:

1. a **physics-informed DeLaN-style Lagrangian neural network** with a positive-definite learned mass matrix and an explicit viscous-dissipation term;
2. a **size-matched black-box MLP** that directly maps `(q, q_dot, q_ddot)` to joint torque;
3. the **MuJoCo analytical inverse-dynamics oracle**;
4. optionally, a feedback-only controller as a control ablation.

All learned models must use exactly the same trajectory-level data subsets at **10%, 30%, and 100%**, and all controllers must use the same references, initial conditions, gains, timestep, torque limits, and test trials. The project is successful even if the physics-informed model does not always win; the academically valid contribution is the controlled measurement of **where its structural prior helps or hurts**.

---

## 1. Requirement traceability

| Given project field | Concrete interpretation |
|---|---|
| Project title | Learn inverse dynamics of the two-joint reacher and test whether Lagrangian structure improves low-data prediction and tracking. |
| System | Reuse the plant from `suite.load("reacher", "easy")`; do not mistake its built-in Cartesian reaching reward for the required tracking task. |
| Physics-informed approach | Use a DeLaN-style Lagrangian model whose mass matrix is symmetric positive definite by construction and whose torque is obtained through Euler–Lagrange derivatives. |
| Closed-loop task | Add a custom joint-space reference generator and computed-torque controller. |
| Learned mapping | `f_inv(q, q_dot, q_ddot) -> tau_joint`. During control, the acceleration input is a feedback-corrected command. |
| Required inputs | Two joint angles, two joint velocities, and two desired/commanded joint accelerations. Periodic sine/cosine encoding is allowed as a deterministic representation of the angles. |
| Required output | Two generalized actuator torques in **N·m**, not MuJoCo’s normalized `ctrl` vector. |
| Analytical comparison | Use MuJoCo `mj_inverse` / `qfrc_inverse` as the authoritative simulator oracle and use the hand-derived two-link equation as an independent check. |
| Prediction success | Report inverse-torque error on held-out in-distribution and out-of-distribution states. |
| Rollout success | Report open-loop state error over exactly 2.0 seconds under held-out torque sequences. |
| Tracking success | Report joint tracking RMSE and success over the same 10 trials for every model/budget; also report an OOD set of 10 trials. |
| Data efficiency | Train on nested 10%, 30%, and 100% trajectory subsets and plot learning curves. |
| Generalization | Test states outside the training envelope while staying inside the physical joint limits and away from active constraints. |

---

## 2. Exact plant being learned

### 2.1 Reproducibility target

Use and record:

- `dm-control==1.0.52`;
- `mujoco==4.0.1`;
- Python version and operating system;
- reacher XML SHA-256;
- all random seeds;
- physics and control timesteps;
- generated-data configuration and code commit/hash.

The current workspace virtual environment uses Python 3.14.4. MuJoCo 4.0.1 publishes Python 3.14 wheels. The old dependency pins in the public DeLaN repository should not be copied wholesale; its equations and tests are useful, but a small local implementation is safer for this two-DoF project.

### 2.2 State, action, and timing

For the pinned reacher model:

- `q = [q_shoulder, q_wrist]`, shape `(2,)`, radians;
- `q_dot = [dq_shoulder, dq_wrist]`, shape `(2,)`, rad/s;
- `q_ddot`, shape `(2,)`, rad/s²;
- `ctrl`, shape `(2,)`, bounded to `[-1, 1]`;
- physics timestep = control timestep = `0.02 s` (50 Hz);
- the shoulder is unlimited;
- the wrist range is `[-2.7925268, 2.7925268] rad`;
- joint damping is `0.01 N·m·s/rad` on both joints;
- contacts are disabled, but the wrist joint-limit constraint still exists.

The built-in observation also contains `to_target`, but that variable must **not** enter the inverse-dynamics model: the target is fixed to the world, has no degree of freedom, and cannot affect the arm dynamics when contacts are disabled.

### 2.3 Torque semantics—the most important implementation detail

The stock actuator relationship is

```text
ctrl                       in [-1, 1]
actuator_force = ctrl
tau_joint = qfrc_actuator = 0.05 * ctrl   [N·m]
```

Therefore:

```text
ctrl_command = clip(tau_command / 0.05, -1, 1)
```

The supervised target must be a generalized joint torque such as `qfrc_inverse` or synchronized `qfrc_actuator`. It must never be mislabeled `data.ctrl`.

### 2.4 Smooth analytical dynamics

Away from the wrist limit, the pinned model has

\[
\tau = M(q)\ddot q+c(q,\dot q)+0.01\dot q,
\]

with

\[
M(q)=\begin{bmatrix}
A+2B\cos q_2 & D+B\cos q_2\\
D+B\cos q_2 & D
\end{bmatrix},
\]

\[
c(q,\dot q)=\begin{bmatrix}
-B\sin q_2(2\dot q_1\dot q_2+\dot q_2^2)\\
B\sin q_2\dot q_1^2
\end{bmatrix},
\]

and the compiled coefficients

```text
A = 9.7581009413152562e-4 kg·m²
B = 2.7394687939302998e-4 kg·m²
D = 1.8867358279909104e-4 kg·m²
```

Gravity torque is zero because both joints rotate about vertical axes and all moving centers remain in a horizontal plane. This matters scientifically: the experiment tests learned inertia, Coriolis/centrifugal coupling, and dissipation, but it does not provide a meaningful nonzero gravity/potential-energy challenge.

Near an active wrist limit, constraint force changes the target:

\[
\tau_{required}=M\ddot q+qfrc_{bias}-qfrc_{passive}-qfrc_{constraint}.
\]

The primary experiment should exclude this regime and report limit behavior separately, if tested at all.

---

## 3. Scientific questions and hypotheses

The report should answer four questions:

1. **Prediction:** Does the Lagrangian model reduce held-out torque error relative to a black-box MLP?
2. **Data efficiency:** Is any advantage larger with 10% or 30% of the data than with 100%?
3. **Generalization:** Does the structured model extrapolate better to unseen joint configurations and speeds?
4. **Control:** Do offline torque improvements translate into lower computed-torque tracking error and more successful trials under identical feedback gains?

Appropriate hypotheses are conditional, not predetermined conclusions:

- H1: physics structure will improve low-data inverse-torque prediction;
- H2: positive-definite structured dynamics will produce more reliable forward rollouts;
- H3: the structured model’s advantage will be larger OOD than in interpolation;
- H4: tracking gains will correlate with, but not be identical to, offline torque gains.

---

## 4. Models that must be implemented

### 4.1 MuJoCo analytical oracle

For each prescribed tuple:

1. copy or reuse a dedicated `Physics`/`MjData` object;
2. set `qpos`, `qvel`, and `qacc`;
3. clear controls and external forces;
4. call `mj_inverse`;
5. copy `qfrc_inverse` immediately;
6. reject or separately label active-constraint rows.

The oracle is ground truth for the same simulator, so its near-zero prediction error is a correctness ceiling, not evidence that a learned model should outperform it.

### 4.2 Physics-informed model: DeLaN-style LNN with dissipation

Use the structured Lagrangian

\[
\mathcal L_\theta(q,\dot q)=
\tfrac12\dot q^T M_\theta(q)\dot q-V_\theta(q),
\]

where

\[
M_\theta(q)=L_\theta(q)L_\theta(q)^T.
\]

`L_theta` is lower triangular and its diagonal is `softplus(raw) + epsilon`, which guarantees a symmetric positive-definite mass matrix. The inverse torque is obtained with automatic differentiation:

\[
\hat\tau_{EL}=
\left(\nabla_{\dot q}\nabla_{\dot q}^{T}\mathcal L\right)\ddot q+
\left(\nabla_q\nabla_{\dot q}^{T}\mathcal L\right)\dot q-
\nabla_q\mathcal L.
\]

Add a learned dissipative term:

\[
\hat\tau=
\hat\tau_{EL}+B_\theta\dot q,
\qquad B_\theta=\operatorname{diag}(\operatorname{softplus}(b_\theta)).
\]

This addition is mandatory for a faithful model of the stock reacher’s joint damping. A purely conservative Lagrangian has an avoidable structural mismatch.

Recommended compact architecture:

- angle features: `[sin(q1), cos(q1), sin(q2), cos(q2)]`;
- shared trunk: two hidden layers of width 32;
- smooth activation: `softplus` or `tanh`;
- mass head: three values for the 2×2 Cholesky factor;
- potential head: one scalar;
- dissipation: two nonnegative learned coefficients;
- training and derivative diagnostics in `float64`.

Use explicit dimensional output scales (for example, order `1e-3 kg·m²` for inertia and `1e-2 N·m·s/rad` for damping) so the Cholesky and dissipation heads initialize near the plant's numerical scale. Treat these as documented numerical parameterizations, not fixed ground-truth values; the coefficients themselves remain learned.

This is approximately the same parameter scale as a two-layer width-32 black-box MLP. Because the true potential gradient is zero, report `||grad(V_theta)||` as a diagnostic; the absolute potential value is not identifiable and is irrelevant up to an additive constant.

Required physical diagnostics:

- symmetry error of `M_theta`;
- minimum/maximum eigenvalue;
- condition number;
- learned damping coefficients;
- mass-matrix and torque error on ID and OOD grids;
- finite-difference checks of automatic derivatives.

### 4.3 Black-box inverse-dynamics baseline (BB-ID)

Use a direct MLP:

```text
input  = [sin(q), cos(q), normalized q_dot, normalized q_ddot]  # 8 values
output = predicted tau_joint                                   # 2 values
```

Recommended architecture:

- two hidden layers of width 32;
- the same smooth activation used by the structured model;
- approximately matched parameter count;
- identical training tuples, optimizer search budget, early-stopping rule, and torque loss.

The sine/cosine transform is not a physics model; it is a fair coordinate representation that prevents an artificial angle-wrap discontinuity. Both learned models should receive it.

### 4.4 Black-box forward head for the rollout metric (BB-FD)

An inverse-only MLP cannot directly roll the state forward. For an unambiguous 2-second comparison, train a separately named forward MLP on the same records:

```text
input  = [sin(q), cos(q), normalized q_dot, normalized tau]
output = predicted q_ddot
```

Use BB-ID for torque prediction and computed-torque control. Use BB-FD only for the open-loop rollout metric. DeLaN derives both directions from one structured parameterization:

\[
\hat{\ddot q}=M_\theta(q)^{-1}
(\tau-\hat c-\hat g-B_\theta\dot q).
\]

This distinction must appear in the report; otherwise “black-box rollout” is mathematically undefined. A secondary experiment may reconstruct forward dynamics from BB-ID’s acceleration Jacobian, but it should not replace the clearly named BB-FD baseline.

### 4.5 Optional controller ablation

Include a feedback-only PD controller if time permits. It shows how much performance comes from inverse-dynamics feedforward rather than feedback alone. It is not a substitute for the required black-box and analytical comparisons.

---

## 5. Dataset protocol

### 5.1 Primary data source

Use **analytically differentiable joint trajectories** and MuJoCo inverse dynamics:

1. generate smooth multi-sine or quintic joint trajectories;
2. evaluate `q(t)`, `q_dot(t)`, and `q_ddot(t)` analytically at the same timestamps;
3. query `mj_inverse` for required generalized torque;
4. reject active-limit and non-finite rows;
5. retain actuator-feasible trajectories for the controller tests.

This is preferable to finite-differencing velocity because it avoids derivative noise, filtering delay, and temporal misalignment.

### 5.2 Recommended dataset size

Use 5-second trajectories sampled at 50 Hz, with 250 samples per trajectory:

| Split | Trajectories | Samples | Purpose |
|---|---:|---:|---|
| training pool | 100 | 25,000 | nested budget subsets |
| validation | 20 | 5,000 | early stopping and hyperparameter selection |
| ID test | 20 | 5,000 | interpolation evaluation |
| OOD configuration test | 20 | 5,000 | 10 shoulder-symmetry + 10 wrist-inertia trajectories |

The required budgets become:

- **10%:** 10 complete training trajectories = 2,500 samples;
- **30%:** 30 complete trajectories, containing the 10% subset = 7,500 samples;
- **100%:** all 100 trajectories = 25,000 samples.

Create one seeded random ordering of training trajectory IDs per data replicate; take its first 10, first 30, and all 100 trajectories so the budgets are nested without favoring file order. Use the identical ordering for both model classes. Never create 10% and 30% sets by randomly selecting adjacent rows.

### 5.3 Proposed state envelopes

Use rejection sampling to enforce and archive exact ranges. A defensible starting specification is:

#### Training and ID-test envelope

```text
q1 in [-1.5, 1.5] rad
q2 in [-1.2, 1.2] rad
|q_dot_i| <= 2.0 rad/s
|q_ddot_i| <= 8.0 rad/s²
|tau_i| <= 0.045 N·m
```

The `0.045 N·m` threshold leaves 10% headroom below the physical `0.05 N·m` limit.

An analytical corner audit of this rectangular state envelope gives approximate worst-case absolute torques of `0.0367 N·m` at the shoulder and `0.0255 N·m` at the wrist, so the proposed envelope is internally feasible before trajectory-level rejection. Recompute and assert these bounds from the installed model rather than treating the constants as timeless.

#### OOD configuration envelope

Use two named tests:

1. **shoulder-symmetry OOD:** shoulder angles outside `[-1.5,1.5]` while `q2`, speed, and acceleration remain in range. The true plant is rotationally invariant in `q1`, so this tests whether the models discover/respect that symmetry.
2. **wrist-inertia OOD:** `|q2|` primarily in `[1.5,2.3] rad`, with speed and acceleration kept in the training envelope. This is the meaningful configuration extrapolation because the inertia and Coriolis terms depend on `q2`.

Keep `|q2| <= 2.3 rad`, safely away from the `2.7925 rad` wrist limit. Verify `qfrc_constraint` rather than relying only on this numerical margin.

An optional third test may raise frequency/speed outside the training range while keeping configurations in range. It must remain torque feasible and must be reported separately so configuration and velocity extrapolation are not conflated.

### 5.4 Canonical row schema

Each stored row should include:

```text
trajectory_id, split, seed, t,
q[2], q_dot[2], q_ddot[2], tau_joint[2],
qfrc_bias[2], qfrc_passive[2], qfrc_constraint[2],
mass_matrix[2,2], nefc, feasible,
dm_control_version, mujoco_version, xml_sha256,
physics_timestep, control_timestep, integrator
```

Every MuJoCo array must be copied immediately; its Python arrays are mutable zero-copy views.

### 5.5 Leakage prevention

- split by complete trajectory before fitting normalizers;
- fit normalization only on the active 10%, 30%, or 100% training subset;
- keep validation, ID test, OOD test, rollout trials, and tracking trials fixed across models;
- do not tune gains or model hyperparameters on the test trials;
- store and assert disjoint trajectory IDs;
- report both trajectories and sample counts.

---

## 6. Training protocol and fairness

### 6.1 Loss

The primary loss for both inverse models is normalized torque MSE:

\[
\mathcal L_{ID}=\frac{1}{2N}\sum_{n=1}^{N}
\left\|S_\tau^{-1}(\hat\tau_n-\tau_n)\right\|_2^2,
\]

where `S_tau` is computed from the active training subset. Report physical-unit errors even if normalized loss is used for optimization.

For BB-FD, use normalized acceleration MSE. Do not add forward-acceleration labels to BB-ID’s output or describe the two MLP heads as one inverse model.

### 6.2 Optimization

Recommended initial protocol:

- Adam optimizer;
- batch size 256;
- fixed maximum optimizer updates for each budget;
- validation early stopping with a documented patience;
- limited, equal-size learning-rate/weight-decay search per architecture;
- gradient clipping only if applied and reported consistently;
- five independent initialization/data-subset seeds per model and budget.

Use the same nested trajectory subsets for corresponding DeLaN and MLP runs. Record parameter count, optimizer updates, training time, and batch-one inference latency. Equal wall-clock time is not required because second derivatives make the structured model intrinsically more expensive, but computational cost must be reported.

### 6.3 Numerical requirements

- use `solve(M, rhs)`, never form an explicit matrix inverse in production code;
- use smooth activations because Euler–Lagrange training requires first and second derivatives;
- monitor mass-matrix conditioning every epoch or evaluation pass;
- establish output scales for inertia, potential, damping, torque, and acceleration explicitly;
- perform derivative and analytical-equation tests in float64;
- do not silently repair invalid predictions during primary evaluation.

---

## 7. Exact definition of the 2-second rollout metric

This metric must be distinct from closed-loop tracking.

### 7.1 Test construction

- use exactly 2.0 seconds per rollout;
- use 100 control intervals at `0.02 s`;
- use held-out initial states and bounded, band-limited torque sequences;
- evaluate 10 ID rollouts and 10 OOD rollouts;
- apply identical initial states and torque sequences to every model.

### 7.2 Dynamics used

- **analytical:** true MuJoCo/closed-form acceleration;
- **DeLaN:** acceleration obtained by solving its structured learned dynamics;
- **BB-FD:** acceleration predicted by the separately trained forward MLP.

Integrate all three with the same integration routine and internal step. A small fixed-step RK4 routine with an internal step such as `0.002 s`, sampled every `0.02 s`, cleanly separates model error from inconsistent integrators. The true trajectory must be produced by the same integration convention using the analytical acceleration function.

### 7.3 Rollout metrics

For each rollout report:

- joint-position RMSE in radians;
- joint-velocity RMSE in rad/s;
- final state L2 error;
- time until position error first exceeds a declared threshold;
- divergence/non-finite rate.

Aggregate with mean, standard deviation, median, and individual-trial points. Do not report only a visually favorable rollout.

---

## 8. Computed-torque tracking controller

### 8.1 Control law

At every 50 Hz control step, define angular position error consistently and compute

\[
e=q_d-q,\qquad \dot e=\dot q_d-\dot q,
\]

\[
a_{cmd}=\ddot q_d+K_d\dot e+K_pe,
\]

\[
\tau_{cmd}=\hat f^{-1}(q,\dot q,a_{cmd}),
\]

\[
ctrl=\operatorname{clip}(\tau_{cmd}/0.05,-1,1).
\]

Evaluate the inverse model at the **current measured state** `(q, q_dot)`, not only at `(q_d, q_dot_d)`. This is the proper computed-torque/feedback-linearizing form.

For the unlimited shoulder, use a shortest-angle error only if references are represented modulo `2π`; otherwise keep an explicitly unwrapped trajectory and error. Do not change conventions between models.

### 8.2 Gain selection

Choose gains once with the analytical oracle on validation trajectories, then freeze them for every model, budget, seed, and test regime. A principled small search is:

```text
zeta = 1
omega_n in {3, 5, 7} rad/s
Kp = omega_n^2 * I
Kd = 2 * zeta * omega_n * I
```

Select the highest validated bandwidth that keeps oracle tracking stable and torque saturation acceptably low. This avoids arbitrary gain tuning and prevents separately tuned high gains from hiding model differences.

### 8.3 Tracking trials

Use smooth, dynamically feasible 5-second references:

- 10 fixed ID trials;
- 10 fixed OOD trials;
- the same initial perturbations for every model;
- references with analytical position, velocity, and acceleration;
- no active wrist limit;
- archived seeds and trajectory coefficients.

### 8.4 Tracking metrics

Report:

- joint-space RMSE, aggregate and per joint;
- end-effector XY RMSE;
- maximum and final joint error;
- RMS and peak commanded torque;
- torque-saturation fraction;
- wrist-limit activation count;
- divergence/failure count;
- inference latency at batch size one.

### 8.5 Trial success criterion

Pre-register a fixed criterion. A suitable starting definition is:

```text
successful trial if:
  aggregate joint RMSE <= 0.10 rad,
  maximum absolute joint error <= 0.35 rad,
  no NaN/divergence, and
  no wrist-limit activation.
```

Report success as `k/10` for ID and OOD separately. Also report continuous errors; a thresholded success count must not hide near misses or large differences among successful trials.

---

## 9. Measures of success

### 9.1 Inverse-dynamics prediction

For each joint and aggregate:

\[
RMSE_\tau=\sqrt{\frac{1}{2N}\sum_n\|\hat\tau_n-\tau_n\|_2^2}.
\]

Also report:

- MAE;
- normalized RMSE using test-target standard deviation;
- 95th-percentile absolute error;
- maximum error;
- error stratified by `q2`, speed, acceleration, and torque magnitude.

### 9.2 Data efficiency

For every metric, plot 10%, 30%, and 100% curves for both learned models. Report seed-level points and uncertainty, not just the best run. A valid statement is of the form:

> “At 10% data, model A achieved X ± Y torque RMSE versus Z ± W for model B on the fixed OOD set.”

Do not claim generic sample efficiency from one small-data result.

### 9.3 Generalization

Report ID, shoulder-symmetry OOD, and wrist-inertia OOD separately. Combining them into one aggregate would hide whether success comes from a trivial global-rotation symmetry or genuine extrapolation in configuration-dependent inertia.

### 9.4 Closed-loop performance

Report the complete relationship between offline and control metrics:

- torque RMSE versus tracking RMSE;
- rollout RMSE versus tracking RMSE;
- mass-matrix condition number versus failures;
- saturation fraction versus tracking error.

This directly tests whether better one-step regression actually improves control.

---

## 10. Required comparison matrix

| Experiment | Analytical | DeLaN 10/30/100% | BB-ID 10/30/100% | BB-FD 10/30/100% | PD-only |
|---|:---:|:---:|:---:|:---:|:---:|
| inverse-torque ID test | yes | yes | yes | no | no |
| inverse-torque OOD tests | yes | yes | yes | no | no |
| mass/physics diagnostics | yes | yes | optional Jacobian | no | no |
| 2-second open-loop rollout | yes | yes | no | yes | no |
| ID computed-torque tracking | yes | yes | yes | no | optional |
| OOD computed-torque tracking | yes | yes | yes | no | optional |
| 10-trial success | yes | yes | yes | no | optional |

The table makes clear that BB-ID and BB-FD answer different questions while using the same underlying records and budget percentages.

---

## 11. Mandatory validation tests before training

1. **Actuator mapping:** assert `qfrc_actuator == 0.05 * ctrl` for random in-range controls.
2. **Forward/inverse consistency:** at synchronized states, feed `qacc` into `mj_inverse` and verify `qfrc_inverse ≈ qfrc_actuator` when external/constraint forces are zero.
3. **Closed-form consistency:** compare the hand-derived `M`, `c`, and damping torque with MuJoCo at random interior states.
4. **Oracle residual:** verify
   `M @ q_ddot + qfrc_bias - qfrc_passive - qfrc_constraint - qfrc_inverse ≈ 0`.
5. **Temporal alignment:** prove that each stored `q`, `q_dot`, `q_ddot`, and `tau` belongs to the same instant.
6. **No mutable views:** mutate/step MuJoCo after logging and verify stored rows do not change.
7. **Split integrity:** assert no trajectory ID appears in more than one split.
8. **Budget nesting:** assert 10% is a subset of 30%, which is a subset of 100%.
9. **Constraint exclusion:** assert primary rows have zero/negligible `qfrc_constraint` and no active limit.
10. **Feasibility:** verify controller/reference torques respect the declared headroom before closed-loop tests.
11. **Autodiff check:** compare DeLaN gradients/Hessians with central finite differences.
12. **SPD check:** sample a dense ID/OOD angle grid and assert positive mass-matrix eigenvalues.
13. **Controller identity:** verify all models receive identical references, gains, initial states, and torque clipping.

---

## 12. Deliverables the completed course project should contain

### Code

- pinned environment/lock file;
- runtime model inspection script;
- deterministic trajectory and dataset generator;
- MuJoCo inverse-dynamics oracle;
- closed-form dynamics checker;
- DeLaN-style inverse/forward model;
- BB-ID and BB-FD baselines;
- training and evaluation scripts;
- computed-torque controller;
- plotting/table-generation scripts;
- unit and integration tests.

### Data and artifacts

- generated datasets with metadata;
- split manifests and trajectory coefficients;
- model checkpoints for all budgets/seeds;
- serialized normalization statistics;
- raw per-trial results, not only aggregate tables;
- example rollout/tracking videos.

### Report figures

At minimum:

1. system and experiment diagram;
2. learned-model architecture diagram;
3. 10/30/100% torque-error learning curves;
4. ID and OOD torque predictions;
5. 2-second position/velocity rollout plots;
6. computed-torque tracking plots;
7. tracking RMSE and success across 10 trials;
8. mass-matrix eigenvalue/condition-number plots;
9. saturation and failure analysis.

### Report tables

1. exact software/model configuration;
2. dataset envelopes and sample counts;
3. model parameter counts/training time;
4. inverse-dynamics metrics;
5. rollout metrics;
6. tracking and success metrics;
7. ID versus OOD comparison.

---

## 13. Major failure modes to avoid

1. Training against `ctrl` while calling it torque.
2. Mixing desired acceleration with a clipped realized torque label.
3. Reading post-step `q/q_dot` with stale pre-step `q_ddot`.
4. Randomly splitting neighboring points from the same trajectory.
5. Treating the built-in Cartesian target task as joint tracking.
6. Feeding `to_target` into inverse dynamics.
7. Omitting viscous damping from a conservative Lagrangian model.
8. Letting high feedback gains hide feedforward-model differences.
9. Testing “OOD” only in shoulder angle, where the true dynamics are invariant.
10. Mixing active joint-limit samples with smooth rigid-body samples.
11. Comparing learned torque to `ctrl` without the `0.05` gear conversion.
12. Claiming that positive-definite learned inertia guarantees closed-loop stability.
13. Describing a separate forward MLP as though an inverse MLP rolled forward directly.
14. Selecting the best seed and hiding variance or failed rollouts.
15. Claiming that the learned decomposition equals uniquely identified physical parameters.

---

## 14. Scope boundary

The core project should **not** expand into reinforcement learning, Cartesian motion planning, contact learning, hardware deployment, formal robust-control proofs, or large robot models. The strongest course-level contribution is a rigorous, reproducible regime map for a two-link arm:

- when Lagrangian structure helps with limited data;
- whether it improves extrapolation;
- whether an explicit damping term is necessary;
- whether offline prediction gains survive open-loop rollout and closed-loop tracking.

The appropriate project claim is:

> We conduct a controlled study of physics-structured inverse-dynamics learning for the `dm_control` two-link reacher. Using matched data budgets, trajectory-level splits, model capacities, and controller settings, we compare a dissipative DeLaN-style model with black-box neural and MuJoCo analytical baselines in inverse-torque prediction, two-second rollout, and in-/out-of-distribution computed-torque tracking.

---

## 15. Primary sources

- DeepMind reacher task source: <https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py>
- DeepMind reacher MJCF: <https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml>
- MuJoCo computation and actuation: <https://mujoco.readthedocs.io/en/4.0.1/computation/index.html>
- MuJoCo function API: <https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html>
- Lutter, Ritter, and Peters, “Deep Lagrangian Networks”: <https://arxiv.org/html/1907.04490>
- Cranmer et al., “Lagrangian Neural Networks”: <https://arxiv.org/html/2003.04630>
- DeLaN author implementation: <https://github.com/milutter/deep_lagrangian_networks>
- Gupta et al., “Structured Mechanical Models for Robot Learning and Control”: <https://proceedings.mlr.press/v120/gupta20a.html>
- Tedrake, “Manipulator Control”: <https://manipulation.csail.mit.edu/force.html>
- Dalla Libera et al., “Forward Dynamics Estimation from Data-Driven Inverse Dynamics Learning”: <https://arxiv.org/html/2307.05093v1>
- Trinh et al., “Newtonian and Lagrangian Neural Networks”: <https://arxiv.org/html/2506.17994v1>

The earlier detailed evidence review remains in:

- `research_notes/Physics informed reacher inverse dynamics/dm_control_and_mujoco.md`
- `research_notes/Physics informed reacher inverse dynamics/literature_and_code.md`
- `research_notes/Reacher inverse dynamics requirements/source_addendum.md`
