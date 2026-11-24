# Phase 1 Viva Handbook

**Project:** Physics-Informed Inverse Dynamics Learning for Data-Efficient Reacher Arm Tracking  
**Phase covered:** Simulator, analytical dynamics, trajectory generation, dataset construction, and validation  
**Validated stack:** Python 3.12.3, `dm-control==1.0.52`, `mujoco==4.0.1`

## How to Use This Handbook

This handbook is designed for explaining Phase 1 during a viva, demonstration, or project review.

Use it in three layers:

1. Memorize the **thirty-second explanation** for the opening question.
2. Understand the **methodology sections** so every design choice can be defended.
3. Practice the **viva questions** without reading the answers word for word.

The best viva answers follow this pattern:

> Define the idea → explain why it matters → describe what we implemented → give evidence that it works.

## Thirty-Second Project Explanation

> Our project learns the inverse dynamics of a simulated two-joint robot arm. Inverse dynamics means calculating the joint torques required for known joint positions, velocities, and desired accelerations. During Phase 1, we pinned and verified the MuJoCo reacher model, implemented an independent closed-form dynamics model, generated smooth trajectories with exact derivatives, labeled 40,000 samples using MuJoCo inverse dynamics, created leakage-free 10%, 30%, and 100% training budgets, and validated every label against the analytical equations. All tests pass, no sample activates a joint constraint, and the maximum analytical torque disagreement is approximately `10^-17 N·m`.

## Two-Minute Phase 1 Explanation

> The final project will compare a physics-informed Lagrangian neural network with a normal black-box neural network for predicting robot joint torque and controlling trajectory tracking. Before training either network, we needed a trustworthy physics and data foundation.
>
> We use DeepMind Control Suite's `reacher/easy` plant, which is a two-joint horizontal arm. The stock task is Cartesian target reaching, but we use only its physical model and later build a separate joint-space tracking controller.
>
> A critical discovery was that MuJoCo's action `ctrl` is not joint torque. Each motor has gear `0.05`, so generalized actuator torque is `0.05 × ctrl`, with a limit of `±0.05 N·m`. We use `qfrc_inverse` as the supervised torque label.
>
> We independently derived the exact two-link mass matrix, Coriolis and centrifugal bias, and viscous damping. We then compared those equations against MuJoCo at hundreds of random states. This prevents circular validation because the independent equation and MuJoCo implementation must agree.
>
> We generated 160 smooth five-second multi-sine trajectories. Their positions, velocities, and accelerations are computed analytically rather than through noisy finite differences. The split contains 100 training, 20 validation, 20 normal test, and 20 out-of-distribution trajectories. Complete trajectories are kept together to prevent temporal leakage.
>
> The final dataset has 40,000 feasible samples, no active constraints, deterministic nested data budgets, separate training-only normalization statistics, and complete metadata. Ten automated tests and the full Phase 1 acceptance report pass.

## Phase 1 Objective

Phase 1 answers one question:

> Can we prove that every future model will train and be evaluated on correct, synchronized, reproducible robot-dynamics data?

Phase 1 deliberately does **not** train the neural models. Training on an incorrect torque definition, misaligned acceleration, leaked split, or active joint-limit force would invalidate every later result regardless of neural-network quality.

The Phase 1 completion criteria were:

- exact software and XML identification;
- correct state, control, and torque spaces;
- synchronized MuJoCo forward and inverse dynamics;
- an independent analytical dynamics implementation;
- smooth, feasible trajectories with exact derivatives;
- disjoint trajectory-level splits;
- nested 10%, 30%, and 100% budgets;
- training-only normalization statistics;
- deterministic serialization and content hashing;
- automated physics and dataset tests.

## System Under Study

The physical plant is loaded from:

```python
suite.load("reacher", "easy")
```

### Important plant properties

| Property | Value |
|---|---|
| Degrees of freedom | 2 |
| Joints | Shoulder, wrist |
| Joint type | Revolute hinge |
| Motion plane | Horizontal XY plane |
| Physics timestep | `0.02 s` |
| Control timestep | `0.02 s` |
| Control frequency | 50 Hz |
| Shoulder limit | Unlimited |
| Wrist limit | `±160° = ±2.7925268 rad` |
| Joint damping | `0.01 N·m·s/rad` per joint |
| Control range | `[-1,1]` per motor |
| Motor gear | `0.05` |
| Generalized torque limit | `±0.05 N·m` per joint |
| Contacts | Disabled |
| Active joint-limit possibility | Yes, at the wrist bound |

### Built-in task versus this project

The built-in `easy` task:

- randomizes a Cartesian target;
- observes the fingertip-to-target vector;
- gives a sparse target-overlap reward.

This project:

- reuses the same robot body and dynamics;
- does not use reinforcement learning;
- does not use `to_target` as a dynamics input;
- creates joint-space reference trajectories;
- learns torque and later performs computed-torque tracking.

The target cannot influence arm dynamics because it is fixed to the world and contacts are disabled.

## Core Dynamics Theory

### General MuJoCo equation

MuJoCo describes continuous dynamics as:

\[
M(q)\dot v+c(q,v)=\tau+J(q)^Tf.
\]

For this arm, `q_dot = v` because both joints are scalar hinges. In the smooth interior, with no external force or active constraint:

\[
M(q)\ddot q+c(q,\dot q)=\tau_{actuator}+\tau_{passive}.
\]

MuJoCo joint damping creates passive force:

\[
\tau_{passive}=-0.01\dot q.
\]

Therefore, the motor torque required to produce a prescribed acceleration is:

\[
\boxed{\tau_{actuator}=M(q)\ddot q+c(q,\dot q)+0.01\dot q.}
\]

### Exact mass matrix

Let `q1` be shoulder angle and `q2` be relative wrist angle:

\[
M(q)=
\begin{bmatrix}
A+2B\cos q_2 & D+B\cos q_2\\
D+B\cos q_2 & D
\end{bmatrix},
\]

where:

```text
A = 9.7581009413152562e-4 kg·m²
B = 2.7394687939302998e-4 kg·m²
D = 1.8867358279909104e-4 kg·m²
```

### Coriolis and centrifugal bias

\[
c(q,\dot q)=
\begin{bmatrix}
-B\sin q_2(2\dot q_1\dot q_2+\dot q_2^2)\\
B\sin q_2\dot q_1^2
\end{bmatrix}.
\]

### Why gravity torque is zero

Gravity acts vertically along the world Z direction. Both joints rotate around vertical Z axes, and every moving center of mass stays at constant height. Gravity therefore cannot perform virtual work around either joint, so its generalized torque is zero.

Do not say “gravity is disabled.” Gravity exists in MuJoCo, but its projection into these joint coordinates is zero.

### Control is not torque

For the stock motors:

\[
\boxed{\tau_{joint}=0.05\,ctrl.}
\]

So:

```text
ctrl = tau_joint / 0.05
```

The three numerically two-dimensional quantities remain conceptually different:

| Quantity | MuJoCo field | Meaning |
|---|---|---|
| Command | `ctrl` | Bounded motor input |
| Actuator output | `actuator_force` | Force before joint transmission |
| Joint torque | `qfrc_actuator` | Generalized force after transmission |

## Methodology 1: Reproducible Environment

### Method

We pinned the complete runtime rather than relying on unbounded package versions:

```text
Python 3.12.3
dm-control 1.0.52
MuJoCo 4.0.1
NumPy 2.5.5
pytest 9.2.0
```

Reproducibility files:

- `.python-version` selects Python 3.12;
- `pyproject.toml` defines direct dependencies and package entry points;
- `uv.lock` locks the complete environment;
- `requirements-lock.txt` provides a conventional exact-version lock.

### Why Python 3.12?

The initial Python 3.14 environment was tested rather than assumed to work. MuJoCo had a Python 3.14 wheel, but `labmaze==1.0.6`, required by `dm_control`, did not. Pip attempted a Bazel source build and failed because Bazel was not part of the environment.

We selected Python 3.12 because all required binary wheels are available. This is a reproducibility decision, not an arbitrary downgrade.

### Viva point

> Pinning only `dm_control` is insufficient because its MuJoCo requirement is open-ended. We pin Python, `dm_control`, MuJoCo, the XML hash, and the complete transitive environment.

## Methodology 2: Runtime Contract Inspection

### Method

The code does not trust research notes or package version numbers alone. On startup it inspects the compiled model and asserts:

- `nq=2`, `nv=2`, `nu=2`, `na=0`;
- joint names and order;
- wrist range;
- action shape and bounds;
- actuator gears;
- physics and control timestep;
- observation order;
- Euler integrator;
- MuJoCo 4 mass-matrix field/signature;
- exact XML SHA-256.

The XML hash is:

```text
849e1e3dd8e79b8f5796bd6e32b0d7a51b916355584402d8f803d74ad35ad193
```

### Why hash the XML?

The package version identifies a release, while the XML hash identifies the exact plant definition. If geometry, damping, density, motor gear, or limits change, the hash changes and Phase 1 fails immediately.

### Important implementation finding

In the pinned runtime, `reacher.get_model_and_assets()` returns XML as `bytes`, not `str`. The implementation hashes those bytes directly. This was verified at runtime rather than inferred from an older example.

## Methodology 3: Independent Analytical Dynamics

### Method

We implemented the exact two-link equations separately from MuJoCo:

- `closed_form_mass_matrix(q)`;
- `closed_form_bias(q, q_dot)`;
- `closed_form_passive_force(q_dot)`;
- `closed_form_inverse(q, q_dot, q_ddot)`;
- `closed_form_forward(q, q_dot, tau)`.

### Why use an independent equation?

If MuJoCo generated labels and MuJoCo alone checked labels, the validation would be circular. The independent equations provide a second implementation with different code paths. Agreement checks:

- indexing and joint order;
- torque sign;
- damping sign;
- actuator scaling;
- mass-matrix extraction;
- Coriolis/centrifugal formulation.

### Positive-definiteness check

The sampled mass matrix had:

```text
minimum eigenvalue: 4.4034751e-05 kg·m²
maximum eigenvalue: 1.6683424e-03 kg·m²
maximum condition number: 37.88695
```

All minimum eigenvalues are positive, confirming physically valid kinetic energy and an invertible forward-dynamics solve in the tested domain.

## Methodology 4: MuJoCo Inverse-Dynamics Oracle

### Method

For every sample:

1. Set `qpos = q`.
2. Set `qvel = q_dot`.
3. Set `qacc = q_ddot`.
4. Clear controls and external forces.
5. Call `mujoco.mj_inverse`.
6. Copy `qfrc_inverse` as `tau_joint`.
7. Copy mass, bias, passive, and constraint diagnostics.

### Why `qfrc_inverse`?

`qfrc_inverse` is the applied generalized force required for the prescribed acceleration after MuJoCo accounts for passive and constraint forces. Away from constraints and with zero external force, it is the actuator torque the controller must provide.

### Why clear `ctrl`?

Control is not an input to inverse dynamics. We prescribe the kinematics and ask what applied generalized force is required. Clearing control prevents stale state from confusing diagnostics.

### Why copy every array?

MuJoCo Python arrays are views into mutable native memory. If a view were appended directly to a dataset, later simulator calls could change previously stored values. Every returned array is copied, and an automated test proves that an earlier record remains unchanged after another oracle call.

## Methodology 5: Analytical Trajectory Generation

### Multi-sine trajectory

For each joint, the trajectory is:

\[
q(t)=q_0+\sum_{k=1}^{K}a_k\sin(2\pi f_k t+\phi_k).
\]

Its derivatives are exact:

\[
\dot q(t)=\sum_{k=1}^{K}2\pi f_k a_k\cos(2\pi f_k t+\phi_k),
\]

\[
\ddot q(t)=-\sum_{k=1}^{K}(2\pi f_k)^2a_k\sin(2\pi f_k t+\phi_k).
\]

We use three frequency components per joint with seeded amplitudes, frequencies, and phases.

### Why not finite differences?

Finite differences would introduce:

- derivative noise;
- boundary errors;
- phase lag if filtering were used;
- ambiguity between continuous acceleration and MuJoCo's discrete velocity update;
- possible split leakage if neighboring samples crossed a split boundary.

Analytical derivatives eliminate these issues.

### Bounded generation

Every trajectory is automatically scaled and accepted only if it satisfies:

- position envelope;
- `|q_dot_i| <= 2 rad/s`;
- `|q_ddot_i| <= 8 rad/s²`;
- `|tau_i| <= 0.045 N·m`;
- minimum position and velocity excitation;
- the required ID or OOD condition.

### Why use `0.045 N·m` headroom?

The physical limit is `0.05 N·m`. The smaller threshold reserves 10% margin for feedback corrections and numerical/model errors during later control experiments.

## Methodology 6: Leakage-Free Dataset Design

### Dataset composition

| Split | Trajectories | Samples | Purpose |
|---|---:|---:|---|
| Training | 100 | 25,000 | Model fitting and budget study |
| Validation | 20 | 5,000 | Early stopping and model selection |
| ID test | 20 | 5,000 | Interpolation evaluation |
| Shoulder OOD | 10 | 2,500 | Rotational-symmetry generalization |
| Wrist OOD | 10 | 2,500 | Configuration-dependent inertia generalization |
| **Total** | **160** | **40,000** | |

Each trajectory contains 250 samples over five seconds at 50 Hz.

### Why split by trajectory?

Adjacent points in a smooth trajectory are strongly correlated. A random row split would put nearly identical states in training and test data, producing artificially low test error. We assign complete trajectory IDs to one split only.

### Nested budgets

A seeded shuffle creates one training-trajectory order:

- 10% uses the first 10 trajectories;
- 30% uses the first 30 and therefore contains the 10% set;
- 100% uses all 100.

This ensures that differences across budgets are caused by adding data rather than replacing one random subset with another.

## Methodology 7: Generalization Test Design

### Shoulder-symmetry OOD

Training shoulder angles stay within the normal range, while shoulder OOD trajectories remain outside it. The true dynamics are independent of absolute shoulder angle because rotating the whole horizontal arm does not change inertia relative to gravity.

This is a test of whether the model discovers or respects a known symmetry.

### Wrist-inertia OOD

Wrist OOD trajectories remain around large positive or negative relative wrist angles, separated from the training range and safely inside the physical limit.

This is the harder and more meaningful extrapolation because:

\[
M(q) \text{ and } c(q,\dot q)
\]

depend on `sin(q2)` and `cos(q2)`.

### Why report them separately?

A model could perform well on shoulder OOD simply because the true function is invariant there, while failing on unseen `q2` where the actual inertia changes. Combining both tests would hide that distinction.

## Methodology 8: Normalization and Provenance

### Separate normalizers

Each budget has its own training-only statistics:

```text
normalization_10.json
normalization_30.json
normalization_100.json
```

Statistics include mean, standard deviation, minimum, and maximum for:

- sine/cosine angle features;
- raw angles;
- velocity;
- acceleration;
- torque.

### Why fit a normalizer per budget?

Using statistics from the 100% set for the 10% model would leak information from trajectories the 10% model is supposed not to see. Test and validation data are never used to fit normalization.

### Provenance artifacts

- `metadata.json`: versions, hash, schema, counts, quality summary;
- `trajectory_manifest.json`: every trajectory coefficient and observed envelope;
- `split_manifest.json`: exact split IDs;
- `budget_manifest.json`: exact nested budget IDs;
- content SHA-256: deterministic hash over names, dtypes, shapes, and bytes.

## Methodology 9: Layered Verification

Verification is layered so one check cannot hide another failure.

### Layer 1: Runtime assertions

The installed software and compiled model must match the experiment contract.

### Layer 2: Unit tests

Ten automated tests cover:

- runtime properties;
- torque/control conversion;
- analytical versus MuJoCo dynamics;
- forward/inverse consistency;
- copied array ownership;
- trajectory bounds;
- exact derivative reproduction;
- deterministic generation;
- dataset round trip;
- accidental overwrite protection.

### Layer 3: Full analytical dataset audit

All 40,000 stored rows are compared against vectorized closed-form mass, bias, passive force, and torque equations.

### Layer 4: Native relabeling

A deterministic random subset of stored rows is sent through a fresh MuJoCo oracle. Stored and newly generated torque labels must match.

### Layer 5: Split, budget, and normalization audit

The validator proves:

- pairwise-disjoint split IDs;
- exact split counts;
- nested budgets;
- complete training coverage at 100%;
- correct sample counts;
- exact regeneration from serialized trajectory coefficients;
- normalization computed from the declared rows only.

### Why report both absolute and relative tolerance?

Torque and mass comparisons are near machine precision. Forward acceleration requires solving a small-inertia matrix, which can amplify floating-point roundoff in absolute units. The largest observed acceleration disagreement is `1.36e-12 rad/s²`, which passes the declared combined absolute and relative criterion.

## Validated Phase 1 Results

The machine-readable result is in `artifacts/phase1_validation.json`.

### Runtime

```text
Python: 3.12.3
dm-control: 1.0.52
MuJoCo Python/library: 4.0.1 / 4.0.1
nq, nv, nu, na: 2, 2, 2, 0
physics timestep: 0.02 s
control timestep: 0.02 s
integrator: mjINT_EULER
```

### Dataset

```text
trajectories: 160
samples: 40,000
all rows feasible: true
active constraints: zero
maximum constraint force: 0.0
maximum |tau1|: 0.0242553793 N·m
maximum |tau2|: 0.0204914396 N·m
```

### Numerical agreement

```text
maximum random-state mass-matrix error: 8.67e-19 kg·m²
maximum random-state bias error: 2.17e-18 N·m
maximum random-state inverse-torque error: 6.94e-18 N·m
maximum equation residual: 3.47e-18 N·m
maximum stored torque-label error: 8.67e-18 N·m
native stored-label recheck error: 0.0 N·m
temporal alignment error: 0.0
normalization reproduction error: 0.0
```

### Reproducibility

Dataset content SHA-256:

```text
f0cdd9a227a9a643b15d44dad61e680d5faf664a0de2c8fc68506be593e78299
```

Test result:

```text
10 passed
```

## File and Artifact Map

| Path | Viva explanation |
|---|---|
| `configs/phase1.toml` | Single source of experimental ranges, counts, seeds, versions, and tolerances |
| `src/reacher_id/environment.py` | Loads and verifies the exact simulator plant |
| `src/reacher_id/dynamics.py` | MuJoCo oracle and independent analytical equations |
| `src/reacher_id/trajectories.py` | Smooth deterministic trajectories with exact derivatives |
| `src/reacher_id/dataset.py` | Labeling, splits, budgets, normalizers, metadata, and serialization |
| `src/reacher_id/validation.py` | Full Phase 1 acceptance audit |
| `src/reacher_id/cli.py` | Reproducible command-line interface |
| `tests/` | Automated runtime, physics, trajectory, and data tests |
| `data/processed/DATA_CARD.md` | Human-readable dataset description |
| `data/processed/*.json` | Machine-readable manifests and provenance |
| `data/processed/reacher_inverse_dynamics.npz` | Labeled numerical dataset |
| `artifacts/runtime_inspection.json` | Recorded installed-model facts |
| `artifacts/phase1_validation.json` | Evidence that all gates passed |
| `uv.lock` | Complete reproducible package resolution |

## Live Demonstration Sequence

Do not regenerate the entire dataset first during a short viva. Use this sequence:

### 1. Explain the system

Show the reacher arm or XML and state:

> Two revolute joints, horizontal motion, 50 Hz, viscous damping, and `±0.05 N·m` torque limits.

### 2. Inspect the runtime

```bash
reacher-phase1 inspect
```

Point out versions, dimensions, gears, timesteps, integrator, and XML hash.

### 3. Show dataset structure

Open:

```text
data/processed/DATA_CARD.md
data/processed/split_manifest.json
data/processed/budget_manifest.json
```

Explain complete-trajectory splitting and nested budgets.

### 4. Run validation

```bash
reacher-phase1 validate
```

Point out `status: passed`, zero constraints, numerical errors, and content hash.

### 5. Run tests

```bash
pytest
```

### 6. Mention full reproducibility command

```bash
reacher-phase1 all --force
```

Use the full command only if time permits. It regenerates and revalidates everything.

## Viva Questions and Model Answers

### 1. What is inverse dynamics?

Inverse dynamics calculates the generalized forces or torques required to produce prescribed position, velocity, and acceleration. Here the mapping is `(q, q_dot, q_ddot) -> tau_joint`.

### 2. How is forward dynamics different?

Forward dynamics takes the current state and applied torque and computes acceleration: `(q, q_dot, tau) -> q_ddot`. Inverse dynamics is usually easier to supervise because acceleration enters robot rigid-body torque linearly through the mass matrix.

### 3. Why is `ctrl` not the learning target?

`ctrl` is the actuator command. The motor transmission has gear `0.05`, so the actual generalized joint torque is `qfrc_actuator = 0.05 * ctrl`. The conventional inverse-dynamics output is joint-space torque in N·m.

### 4. Why use `qfrc_inverse` as the label?

It is MuJoCo's required applied generalized force for the prescribed acceleration after accounting for passive and constraint forces. In our unconstrained, zero-external-force samples, it corresponds to required actuator joint torque.

### 5. Why not use the built-in target observation?

The target is not a dynamic state of the arm. It is fixed to the world and contacts are disabled, so `to_target` cannot causally affect required joint torque.

### 6. Is gravity disabled?

No. Gravity exists, but the arm rotates in a horizontal plane around vertical axes. The centers of mass do not change height, so generalized gravity torque is zero.

### 7. Why does damping appear with a positive sign in required motor torque?

MuJoCo passive damping force is `-0.01 q_dot`, opposing motion. The actuator must overcome it, so inverse actuator torque contains `+0.01 q_dot`.

### 8. Why implement closed-form dynamics if MuJoCo already has dynamics?

It gives an independent validation path. It catches wrong indexing, signs, units, transmission factors, and stale simulator fields. Without it, MuJoCo would both create and judge its own labels.

### 9. Why generate trajectories instead of independent random points?

The final use case is trajectory tracking, and coherent trajectories provide physically meaningful combinations of position, velocity, and acceleration. They also allow leakage-free splitting and later rollout/control tests.

### 10. Why multi-sine trajectories?

They are smooth, persistently exciting, easy to randomize, and analytically differentiable. Multiple frequencies excite inertia, velocity coupling, and damping over a broad state range.

### 11. Why not estimate acceleration from velocity differences?

Finite differences add noise and discretization error. MuJoCo's Euler integrator also treats damping implicitly, so a finite velocity increment is not necessarily identical to the instantaneous continuous acceleration needed by inverse dynamics.

### 12. Why split by entire trajectory?

Adjacent samples are highly correlated. Row-level random splitting would place near-duplicate points in training and testing and make generalization appear better than it is.

### 13. Why are the 10%, 30%, and 100% sets nested?

Nested sets isolate the effect of adding data. If every budget used unrelated trajectories, differences could be caused by subset difficulty rather than data quantity.

### 14. Why use separate normalization for each budget?

The 10% model must not receive statistics calculated from the remaining 90% of training trajectories. That would be a subtle form of data leakage.

### 15. What does shoulder OOD test?

It tests generalization outside the observed absolute shoulder-angle range where true dynamics are rotationally invariant.

### 16. What does wrist OOD test?

It tests real configuration extrapolation because the mass and Coriolis terms vary with relative wrist angle through sine and cosine.

### 17. Why avoid the wrist limit?

At an active limit, MuJoCo adds constraint force. The smooth Euler–Lagrange rigid-body model would then be learning a mixture of normal arm dynamics and unilateral limit dynamics. The primary study intentionally isolates smooth inverse dynamics.

### 18. Why keep torque below `0.045 N·m`?

The actuator limit is `0.05 N·m`. The smaller threshold provides headroom for feedback correction and model error during tracking.

### 19. How do you prove the data are synchronized?

Position, velocity, and acceleration are evaluated analytically at one timestamp and passed together to `mj_inverse`. The trajectory coefficients are serialized, then every stored trajectory is regenerated and compared exactly during validation.

### 20. How do you know old MuJoCo rows are not being overwritten?

Every native array is copied immediately. A test stores one result, invokes the oracle at another state, and confirms the first result is unchanged.

### 21. Why use an XML hash in addition to package versions?

Versions identify software releases; the hash identifies the exact robot definition. A geometry, damping, density, gear, or limit change alters the hash.

### 22. Why was Python 3.14 rejected?

MuJoCo supported it, but the complete `dm_control` dependency graph did not: `labmaze` lacked a compatible wheel and required an unavailable Bazel build. Python 3.12 produced a complete locked binary environment.

### 23. What does `qfrc_bias` contain?

It contains Coriolis, centrifugal, and gravitational generalized forces. For this arm, its gravity component is zero.

### 24. What does `qfrc_passive` contain?

It contains passive forces such as joint damping. Here it is `-0.01 q_dot`.

### 25. What does `qfrc_constraint` contain?

It contains generalized force from active constraints such as the wrist joint limit. It is zero for every primary dataset row.

### 26. Is 40,000 samples automatically 40,000 independent samples?

No. Time samples within one trajectory are correlated. That is why we report both sample count and trajectory count and make data budgets at trajectory level.

### 27. How is deterministic reproduction verified?

All random generators use recorded seeds, every trajectory coefficient is stored, budgets use a fixed shuffle seed, and a content hash is computed from array names, dtypes, shapes, and bytes.

### 28. What is the most important Phase 1 result?

We can prove that model training will use the intended generalized torque with correct units, synchronized kinematics, no constraints, no split leakage, and independent analytical agreement near floating-point precision.

### 29. What remains after Phase 1?

Phase 2 implements and trains the DeLaN-style inverse model, black-box inverse model, and black-box forward rollout baseline at all three budgets. Phase 3 integrates computed-torque control and performs tracking trials and the final demonstration.

### 30. What is one limitation of Phase 1?

The data are clean simulation data with exact acceleration. They do not model encoder noise, acceleration filtering, actuator lag, backlash, or hardware friction beyond MuJoCo's viscous damping.

## Equation and Terminology Cheat Sheet

| Term | Meaning |
|---|---|
| `q` | Joint position `[shoulder, wrist]`, radians |
| `q_dot` | Joint velocity, rad/s |
| `q_ddot` | Joint acceleration, rad/s² |
| `tau_joint` | Generalized actuator torque, N·m |
| `ctrl` | Bounded MuJoCo actuator command |
| `M(q)` | Symmetric positive-definite joint-space inertia matrix |
| `c(q,q_dot)` | Coriolis, centrifugal, and gravity bias; gravity is zero here |
| `qfrc_passive` | Passive generalized force, `-0.01 q_dot` here |
| `qfrc_constraint` | Generalized active-constraint force |
| `qfrc_inverse` | Required applied generalized force from inverse dynamics |
| ID | In distribution |
| OOD | Out of distribution |

Essential equations:

\[
\tau=M(q)\ddot q+c(q,\dot q)+0.01\dot q
\]

\[
\tau=0.05\,ctrl
\]

\[
\ddot q=M(q)^{-1}[\tau-c(q,\dot q)-0.01\dot q]
\]

Dataset dimensions:

```text
q:               (40000, 2)
q_dot:           (40000, 2)
q_ddot:          (40000, 2)
tau_joint:       (40000, 2)
mass_matrix:     (40000, 2, 2)
constraint data: (40000, ...)
```

## Common Mistakes to Avoid in the Viva

Do not say:

- “The action is torque.”
- “Gravity is turned off.”
- “The built-in easy task already tracks joint trajectories.”
- “Every time sample is statistically independent.”
- “We randomly split all rows.”
- “Desired acceleration was estimated by finite differences.”
- “MuJoCo and the analytical model are the same implementation.”
- “The target position affects inverse dynamics.”
- “Positive-definite mass guarantees controller stability.”
- “The neural network has already been trained in Phase 1.”

Say instead:

- “The control maps to torque through gear `0.05`.”
- “Gravity projects to zero generalized torque for horizontal motion.”
- “We reuse the plant and build a custom tracking task later.”
- “We split and budget complete trajectories.”
- “Acceleration is the exact second derivative of the reference.”
- “The independent closed form cross-checks MuJoCo.”
- “Phase 1 proves label and experiment integrity before training.”

## Resources Used and Why

### Primary simulator sources

| Resource | How it was used |
|---|---|
| [`reacher.py` at dm_control 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py) | Verified task factory, reset, observation fields, target behavior, and 20-second default task |
| [`reacher.xml` at dm_control 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml) | Verified geometry, joints, damping, motor gear, control limits, timestep, and disabled contacts |
| [MuJoCo 4.0.1 computation chapter](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html) | Defined the continuous equations, actuation spaces, passive forces, constraints, and integrator semantics |
| [MuJoCo 4.0.1 function API](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html) | Verified `mj_forward`, `mj_inverse`, and `mj_fullM` responsibilities |
| [MuJoCo Python API](https://mujoco.readthedocs.io/en/4.0.1/python.html) | Verified native/wrapper calls and mutable zero-copy array behavior |
| [`mjdata.h` at MuJoCo 4.0.1](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h) | Verified exact meanings of force, acceleration, inverse, and mass-matrix fields |

### Physics-informed learning resources

| Resource | How it informed the project |
|---|---|
| [Lutter et al., Deep Lagrangian Networks](https://arxiv.org/html/1907.04490) | Motivated structured inverse dynamics, positive-definite inertia, forward/inverse reuse, and tracking evaluation |
| [Cranmer et al., Lagrangian Neural Networks](https://arxiv.org/html/2003.04630) | Clarified Euler–Lagrange automatic derivatives, smooth activations, and distinction from DeLaN |
| [Gupta et al., Structured Mechanical Models](https://proceedings.mlr.press/v120/gupta20a.html) | Supported explicit treatment of non-conservative generalized forces and limited-data comparison |
| [Tedrake, Manipulator Control](https://manipulation.csail.mit.edu/force.html) | Supported the later computed-torque control formulation and distinction between inverse dynamics and PD control |

### Environment and package resources

| Resource | How it was used |
|---|---|
| [dm-control 1.0.52 PyPI metadata](https://pypi.org/project/dm-control/1.0.52/) | Verified dependency requirements and release identity |
| [MuJoCo 4.0.1 PyPI metadata](https://pypi.org/project/mujoco/4.0.1/) | Verified Python wheel support and exact binding version |
| Runtime installation test | Revealed the Python 3.14 `labmaze`/Bazel incompatibility and justified Python 3.12 |

### Internal research and evidence

- `research_notes/Physics informed reacher inverse dynamics/dm_control_and_mujoco.md`
- `research_notes/Physics informed reacher inverse dynamics/literature_and_code.md`
- `research_notes/Reacher inverse dynamics requirements/source_addendum.md`
- `reports/Reacher inverse dynamics requirements.md`
- `artifacts/phase1_validation.json`
- `data/processed/DATA_CARD.md`

## Final Phase 1 Summary

Phase 1 produced a verified experimental foundation rather than merely a data file.

We established:

1. **What system is being learned:** the exact pinned two-joint reacher plant.
2. **What the neural target means:** generalized joint torque in N·m.
3. **How control maps to torque:** `tau = 0.05 * ctrl`.
4. **What the true equations are:** inertia, Coriolis/centrifugal coupling, and viscous damping with zero gravity torque.
5. **How labels are generated:** synchronized prescribed kinematics through `mj_inverse`.
6. **How labels are independently checked:** exact closed-form two-link dynamics.
7. **How data leakage is prevented:** complete trajectory splits and nested budgets.
8. **How extrapolation is tested:** separate shoulder-symmetry and wrist-inertia OOD regimes.
9. **How reproducibility is enforced:** locked dependencies, seeds, manifests, XML hash, and dataset content hash.
10. **What evidence supports completion:** all 10 tests and the complete acceptance audit pass.

A concise closing viva statement is:

> Phase 1 ensures that any performance difference observed later belongs to the learned models—not to incorrect torque units, stale simulator values, active constraints, data leakage, or an undocumented environment change.
