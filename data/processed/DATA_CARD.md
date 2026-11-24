# Reacher inverse-dynamics dataset card

## Purpose

This dataset supports supervised learning of the two-joint `dm_control` reacher inverse dynamics:

```text
(q, q_dot, q_ddot) -> tau_joint
```

`tau_joint` is generalized actuator torque in N·m. It is not MuJoCo's normalized `ctrl` value.

## Simulator

- `dm-control==1.0.52`
- `mujoco==4.0.1`
- reacher XML SHA-256: `849e1e3dd8e79b8f5796bd6e32b0d7a51b916355584402d8f803d74ad35ad193`
- physics/control timestep: `0.02 s`
- transmission: `tau_joint = 0.05 * ctrl`

## Composition

| Split | Trajectories | Samples |
|---|---:|---:|
| Training | 100 | 25,000 |
| Validation | 20 | 5,000 |
| In-distribution test | 20 | 5,000 |
| Shoulder-symmetry OOD | 10 | 2,500 |
| Wrist-inertia OOD | 10 | 2,500 |
| **Total** | **160** | **40,000** |

Each trajectory lasts five seconds and contains 250 samples. Complete trajectories—not adjacent rows—define every split and data budget.

## Labels

Smooth multi-sine trajectories provide analytically exact `q`, `q_dot`, and `q_ddot`. MuJoCo `mj_inverse` provides `qfrc_inverse`, stored as `tau_joint`.

Additional diagnostics include:

- mass matrix;
- bias force;
- passive force;
- constraint force;
- active-constraint count;
- feasibility flag.

## Data budgets

- 10%: 10 complete training trajectories / 2,500 samples
- 30%: 30 nested trajectories / 7,500 samples
- 100%: 100 nested trajectories / 25,000 samples

The exact trajectory IDs are in `budget_manifest.json`. Corresponding training-only statistics are in `normalization_10.json`, `normalization_30.json`, and `normalization_100.json`.

## Quality checks

- all 40,000 rows are finite and feasible;
- no row activates a joint constraint;
- maximum stored constraint force is zero;
- all torque labels are below the `0.045 N·m` headroom;
- native MuJoCo relabeling error is zero on the validation sample;
- analytical and stored torque differ by at most `8.67e-18 N·m`;
- serialized analytical trajectories reproduce exactly from their coefficients.

Dataset content SHA-256:

```text
f0cdd9a227a9a643b15d44dad61e680d5faf664a0de2c8fc68506be593e78299
```

See `metadata.json` and `artifacts/phase1_validation.json` for machine-readable provenance and validation results.
