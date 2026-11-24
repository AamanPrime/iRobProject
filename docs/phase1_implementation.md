# Phase 1 implementation: physics and data foundation

Phase 1 is complete when the pinned simulator, independent analytical dynamics, generated trajectories, MuJoCo labels, dataset splits, budget manifests, and normalization statistics all pass the automated acceptance checks.

## Canonical environment

The implementation uses **Python 3.12** in `.venv`.

Python 3.14 was tested first, but `labmaze==1.0.6`—a required `dm_control` dependency—does not publish a Python 3.14 wheel and falls back to a Bazel source build. Python 3.12 has a complete binary-compatible dependency set and is therefore the reproducible project runtime.

Pinned core packages:

```text
dm-control==1.0.52
mujoco==4.0.1
numpy==2.5.5
pytest==9.2.0
```

Both `uv.lock` and `requirements-lock.txt` record the complete transitive environment.

## Setup

With `uv` installed:

```bash
uv sync --frozen --extra dev
source .venv/bin/activate
```

For headless commands:

```bash
export MUJOCO_GL=egl
export LC_ALL=C.UTF-8
```

## Commands

Inspect the installed simulator and assert the runtime contract:

```bash
reacher-phase1 inspect
```

Generate the complete deterministic dataset:

```bash
reacher-phase1 generate --force
```

Run all physics and dataset acceptance checks:

```bash
reacher-phase1 validate
```

Run the whole phase in one command:

```bash
reacher-phase1 all --force
```

Run automated tests:

```bash
pytest
```

## Implemented components

### Runtime contract

`src/reacher_id/environment.py` verifies:

- exact `dm_control` and MuJoCo versions;
- reacher XML SHA-256;
- state/action dimensions;
- joint order and limits;
- action range and motor gears;
- physics and control timesteps;
- observation order;
- Euler integrator;
- MuJoCo 4 mass-matrix API.

### Independent dynamics implementations

`src/reacher_id/dynamics.py` contains:

- synchronized MuJoCo forward dynamics;
- synchronized MuJoCo inverse dynamics;
- dense mass-matrix extraction;
- control-to-torque conversion;
- independent closed-form mass matrix;
- independent Coriolis/centrifugal bias;
- viscous passive force;
- analytical forward and inverse dynamics.

MuJoCo fields are copied immediately so returned records do not alias mutable simulator memory.

### Trajectory generation

`src/reacher_id/trajectories.py` generates deterministic multi-sine trajectories with exact analytical position, velocity, and acceleration.

Every trajectory is checked for:

- configuration bounds;
- velocity bounds;
- acceleration bounds;
- torque headroom;
- minimum excitation;
- correct OOD regime separation.

### Dataset generation

`src/reacher_id/dataset.py` creates:

- 100 training trajectories;
- 20 validation trajectories;
- 20 in-distribution test trajectories;
- 10 shoulder-angle OOD trajectories;
- 10 wrist-configuration OOD trajectories;
- 250 samples per trajectory;
- 40,000 total labeled samples.

The 10%, 30%, and 100% budgets are shuffled once and nested by complete trajectory ID. Normalization statistics are fitted independently using only the rows in each training budget.

### Acceptance validation

`src/reacher_id/validation.py` verifies:

- analytical versus MuJoCo mass matrices;
- analytical versus MuJoCo bias, damping, and inverse torque;
- actuator transmission mapping;
- forward/inverse consistency;
- equation residuals;
- mass-matrix positive definiteness and conditioning;
- owned array copies;
- finite serialized values;
- trajectory-level split disjointness;
- nested data budgets;
- exact analytical derivative alignment;
- native MuJoCo relabeling of random stored rows;
- normalization provenance;
- deterministic content hash.

## Generated artifacts

```text
artifacts/runtime_inspection.json
artifacts/phase1_validation.json
data/processed/reacher_inverse_dynamics.npz
data/processed/metadata.json
data/processed/trajectory_manifest.json
data/processed/split_manifest.json
data/processed/budget_manifest.json
data/processed/normalization_10.json
data/processed/normalization_30.json
data/processed/normalization_100.json
```

## Validated result

The current complete dataset has content hash:

```text
f0cdd9a227a9a643b15d44dad61e680d5faf664a0de2c8fc68506be593e78299
```

Key acceptance results:

```text
status: passed
automated tests: 10 passed
samples: 40,000
trajectories: 160
all rows feasible: true
active constraints: 0
maximum constraint force: 0.0 N·m
maximum |tau1|: 0.0242553793 N·m
maximum |tau2|: 0.0204914396 N·m
maximum inverse-torque analytical error: 6.94e-18 N·m
maximum stored-label analytical error: 8.67e-18 N·m
maximum native relabeling error: 0.0 N·m
minimum sampled mass-matrix eigenvalue: 4.40348e-05 kg·m²
maximum sampled mass-matrix condition number: 37.887
```

These results establish that Phase 2 can train against synchronized generalized torque labels without hidden action scaling, split leakage, active joint constraints, or numerical disagreement between the simulator and independent analytical model.

For oral-exam preparation, methodology explanations, resource attribution, and likely examiner questions, see [`phase1_viva_handbook.md`](phase1_viva_handbook.md).
