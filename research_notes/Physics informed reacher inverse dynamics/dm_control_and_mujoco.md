# Authoritative `dm_control` Reacher and MuJoCo Dynamics Notes

Research snapshot: **2026-11-24**. The reproducibility target used throughout is **`dm-control==1.0.52` with `mujoco==4.0.1`**. `dm_control` 1.0.52 was released on 2026-11-11 specifically to upgrade to MuJoCo 4.0.1, and its package metadata requires `mujoco>=4.0.1`; pinning both exact versions is preferable to accepting that open lower bound. — [dm_control 1.0.52 release](https://github.com/google-deepmind/dm_control/releases/tag/1.0.52); [1.0.52 `setup.py`](https://github.com/google-deepmind/dm_control/blob/1.0.52/setup.py); [PyPI metadata](https://pypi.org/project/dm-control/1.0.52/); [MuJoCo 4.0.1 changelog](https://mujoco.readthedocs.io/en/4.0.1/changelog.html#version-4-0-1-november-11-2026)

## What exactly is `suite.load('reacher', 'easy')`?

### Takeaway

It is a two-DoF, horizontal, planar arm with two directly driven hinge motors. The public observation has three two-vectors (`position`, `to_target`, `velocity`), the action is a bounded two-vector, and both the default physics and control periods are 0.02 s. The built-in task is Cartesian target reaching, not joint-space trajectory tracking. — [reacher task source](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [`control.Environment`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py)

### Cited Findings

#### Factory, episode, and observations

- `suite.load('reacher', 'easy')` dispatches to `reacher.easy()`. That factory loads `reacher.xml`, creates `Reacher(target_size=0.05)`, and constructs a `control.Environment` with a default 20 s time limit. — [`suite.load`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/__init__.py); [`reacher.easy`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py)
- The exact unflattened observation is an ordered mapping:

  | Key | Shape | Meaning |
  |---|---:|---|
  | `position` | `(2,)` | copy of `qpos`, ordered `[shoulder, wrist]`, in radians |
  | `to_target` | `(2,)` | world-frame XY vector `target.geom_xpos[:2] - finger.geom_xpos[:2]` |
  | `velocity` | `(2,)` | copy of `qvel`, ordered `[shoulder, wrist]`, in rad/s |

  `flat_observation=False` by default; if explicitly enabled, `control.Environment` concatenates fields in mapping order into one six-vector. The current distributed MuJoCo build uses double precision, so runtime specs are `float64`. — [`Reacher.get_observation`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [`Physics.position`/`velocity`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py); [`flatten_observation`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py); [MuJoCo numeric type](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APItypes.html#mjtnum)
- Compiling the pinned MJCF produces `nq=2`, `nv=2`, `nu=2`, `na=0`, two joints, and two actuator controls/outputs. Because both joints are scalar hinges, `qvel` is also the ordinary time derivative of `qpos`; the usual MuJoCo distinction between `nq` and `nv` for quaternion joints does not arise here. **Runtime verification is still required after any version/XML change.** — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo state notation](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework)
- At reset, the unlimited shoulder is sampled uniformly from `[-π, π]`, the limited wrist uniformly from its compiled bounds, and velocities remain at MuJoCo's reset value of zero. The target angle is uniform on `[0,2π)` and its radial distance from the shoulder is uniform on `[0.05,0.20]` m (uniform in radius, not uniform in disk area). — [`Reacher.initialize_episode`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [joint randomizer](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/utils/randomizers.py)
- The reward is sparse. Although the `easy` docstring describes a `5e-2` tolerance, the implementation compares finger-to-target **center distance** with the sum of target and finger radii: `0.05 + 0.01 = 0.06` m. It returns exactly 1 for distance `<=0.06` and 0 outside because `rewards.tolerance` has default `margin=0`. — [`Reacher.get_reward`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [`rewards.tolerance`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/utils/rewards.py); [finger and target radii in MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)

#### Joints, geometry, and constraints

- The generalized coordinate order is exactly the XML joint order:

  | Index | Name | Type / axis | Range | Damping | Armature |
  |---:|---|---|---|---:|---:|
  | 0 | `shoulder` | hinge, local `+z` | unlimited | `0.01` | `0` |
  | 1 | `wrist` | hinge, local `+z` | `[-160°,160°] = [-2.792526803,2.792526803]` rad | `0.01` | `0` |

  MJCF angles default to degrees and are compiled into radians. — [joint defaults and wrist declaration](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MJCF angle convention](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#compiler-angle); [hinge semantics](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APItypes.html#mjtjoint)
- The first arm capsule is 0.12 m long with radius 0.01 m. The wrist body is offset 0.12 m from the shoulder. Its visible capsule is 0.10 m long and radius 0.01 m, while the finger center is placed 0.12 m from the wrist, so the kinematic shoulder-to-finger-center reach is 0.24 m. The finger is a radius-0.01 m sphere. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)
- No explicit inertial elements are authored. MuJoCo therefore compiles body masses and inertias from the capsules/sphere using uniform volumetric density; the default geom density is 1000 kg/m³. **The following compiled values were runtime-verified on 1.0.52/4.0.1 and should be re-dumped rather than assumed on another stack:** — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [geom mass/density and inertia inference](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#body-geom-density)

  | Dynamic body | Mass (kg) | Local COM x (m) | Moment about planar z through COM (kg·m²) |
  |---|---:|---:|---:|
  | `arm` | `0.041887902047863912` | `0.06` | `6.3313563945346295e-05` |
  | `hand` | `0.035604716740684321` | `0.05` | `3.9175660390264734e-05` |
  | `finger` | `0.0041887902047863914` | `0` in its body, 0.12 m from wrist | `1.6755160819145565e-07` |

- `<flag contact="disable"/>` disables collision/contact constraints for the arm, target, ground, and walls. It does **not** disable the wrist joint-limit constraint, so `qfrc_constraint` can become nonzero near/at the wrist bound. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo disable flags](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APItypes.html#mjtdisablebit)
- The model leaves gravity at MuJoCo's default `(0,0,-9.81)` m/s², but every motion axis is vertical `z` and all moving centers stay in a horizontal plane. Consequently gravity contributes zero generalized torque for this model; it should nevertheless be checked through `data.qfrc_bias` if the XML is modified. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MJCF option defaults](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#option-gravity)

#### Action and actuator semantics

- `env.action_spec()` is a `float64` bounded array of shape `(2,)`, minimum `[-1,-1]`, maximum `[1,1]`, ordered `[shoulder, wrist]`. `base.Task.before_step` copies each action component directly into the corresponding `data.ctrl` entry; it does not reinterpret the action as a joint angle or normalized policy output. — [`base.Task`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/base.py); [`mujoco.action_spec`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py); [actuator order in MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)
- Both actuators are MuJoCo `motor` shortcuts with fixed gain 1, no bias, no activation dynamics (`na=0`), joint transmission, `gear=0.05`, and `ctrlrange=[-1,1]`. For an in-range action `u`, this specific model therefore has:

  ```text
  data.ctrl          = u                         # control space
  data.actuator_force = u                        # scalar output space
  data.qfrc_actuator  = [0.05*u_shoulder,
                         0.05*u_wrist]            # generalized joint torque
  ```

  Thus the physically relevant joint-torque limit is ±0.05 N·m per joint. `ctrl` and `actuator_force` happen to be numerically equal here, but neither should be mislabeled as generalized torque. — [motor/gear declarations](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo actuation model](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model); [`motor` shortcut reference](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#actuator-motor)
- MuJoCo distinguishes controls (`nu`), actuator force outputs (`nout`), and generalized forces (`nv`). They are all 2 for this reacher, but that equality is model-specific and must not be generalized to tendon, site, multi-input, or multi-output actuators. — [MuJoCo actuation model](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model); [`mjData` fields](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)

#### Timesteps

- The XML physics timestep is `0.02` s. `reacher.easy()` supplies no `control_timestep` or `n_sub_steps`, so `control.Environment` defaults to one physics step per action: the control timestep is also `0.02` s. A 20 s episode therefore permits 1000 action transitions. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [`reacher.easy`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [`control.Environment` timestep logic](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py)
- The XML does not select an integrator, so MuJoCo's default `Euler` integrator is used. This is semi-implicit Euler with joint damping handled implicitly. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [integrator default](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#option-integrator); [Euler details](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#integrators)

#### Built-in task versus proposed tracking experiment

- The built-in task randomizes a **Cartesian target**, exposes finger-to-target XY displacement, and rewards overlap. It defines no desired `q_d(t)`, `q̇_d(t)`, or `q̈_d(t)`, no joint tracking error, and no tracking controller. — [reacher task source](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py)
- A joint-space tracking study can reuse `reacher.Physics` and `reacher.xml`, but it is a new experiment/task. The target is a static worldbody geom and contacts are disabled, so target randomization changes observations/reward/rendering but not arm dynamics. A clean implementation should either create a custom `Task` or operate directly on a copied `Physics` object rather than describe the built-in `easy` task as joint tracking. — [target and contact declarations](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [`Physics.from_xml_string` path used by reacher](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [`base.Task` interface](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/base.py)

### Inferences

- Because the target has no DoF and no enabled contact, the same inverse-dynamics model applies to every built-in target position; including `to_target` in an inverse-dynamics network would add a nuisance input rather than a causal dynamics variable. This follows from the target's placement on the worldbody and disabled contacts. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)
- Raw `q1` is physically periodic and the smooth dynamics below are independent of it; `q2` enters through sine/cosine. A learned model may therefore benefit from `[sin(q1),cos(q1),sin(q2),cos(q2)]` or, for this exact model, only periodic encoding of `q2`, while retaining raw angles for controller bookkeeping. This follows from the planar rotational symmetry and should be validated empirically. — [reacher kinematic tree](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo continuous dynamics](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework)

### Gaps

- `dm_control` does not promise that the reacher MJCF or task constants remain unchanged across releases. Every reproduction should pin versions, hash the loaded XML, and dump compiled model/spec values at runtime. — [dm_control releases](https://github.com/google-deepmind/dm_control/releases); [`get_model_and_assets`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py)
- The project must define whether its symbol `tau` means policy control `ctrl`, scalar actuator output `actuator_force`, generalized actuator torque `qfrc_actuator`, or total generalized applied force. For conventional robot inverse dynamics, the least ambiguous choice is the `(nv,)` generalized joint torque. — [MuJoCo actuation model](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model)

## Which APIs expose state, forces, mass matrix, and analytical dynamics?

### Takeaway

Use direct `physics.data` arrays for synchronized simulator quantities and MuJoCo's `mj_forward`, `mj_inverse`, and `mj_fullM` for analytical dynamics. In a `dm_control.Physics`, pass `physics.model.ptr` and `physics.data.ptr` to native MuJoCo functions; native `mujoco.MjModel/MjData` objects are passed directly without `.ptr`. — [`dm_control` 1.0 migration guide](https://github.com/google-deepmind/dm_control/blob/1.0.52/migration_guide_1.0.md); [MuJoCo Python API](https://mujoco.readthedocs.io/en/4.0.1/python.html#functions)

### Cited Findings

#### Core equations and fields

- MuJoCo's continuous-time equation is

  \[
  M(q)\dot v + c(q,v) = \tau + J(q)^T f,
  \]

  where `qfrc_bias` is `c`, applied force `tau` is the sum of passive, actuation, and user-applied forces, and `qfrc_constraint` is the generalized `Jᵀf` contribution. — [MuJoCo general framework](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework); [`mjData` field definitions](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)
- Relevant current fields are:

  | Quantity | Current access | Shape in reacher | Semantics |
  |---|---|---:|---|
  | `q` | `physics.data.qpos` | `(2,)` | generalized positions |
  | `q_dot` / `v` | `physics.data.qvel` | `(2,)` | generalized velocities |
  | realized instantaneous `q_ddot` | `physics.data.qacc` after a synchronized forward call | `(2,)` | generalized acceleration |
  | command | `physics.data.ctrl` or `physics.control()` | `(2,)` | actuator controls, not joint torque |
  | output-space force | `physics.data.actuator_force` | `(2,)` | force before transmission |
  | generalized actuator torque | `physics.data.qfrc_actuator` | `(2,)` | actuator contribution in joint space |
  | external generalized force | `physics.data.qfrc_applied` | `(2,)` | user-applied joint-space force |
  | external Cartesian wrench | `physics.data.xfrc_applied` | `(nbody,6)` | user-applied body wrenches |
  | bias | `physics.data.qfrc_bias` | `(2,)` | Coriolis + centrifugal + gravity |
  | passive | `physics.data.qfrc_passive` | `(2,)` | damping/spring/other passive force |
  | unconstrained net force | `physics.data.qfrc_smooth` | `(2,)` | smooth applied/passive force minus bias |
  | unconstrained acceleration | `physics.data.qacc_smooth` | `(2,)` | forward acceleration before constraint force |
  | constraint | `physics.data.qfrc_constraint` | `(2,)` | generalized constraint force |
  | inverse output | `physics.data.qfrc_inverse` | `(2,)` | net external + actuation force required by prescribed acceleration |
  | sparse inertia | `physics.data.M` in MuJoCo 4.0.1 | model-dependent | sparse joint-space inertia |

  These arrays are views into mutable MuJoCo memory; `.copy()` is mandatory when logging them across calls. — [`mjData` 4.0.1 header](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h); [Python zero-copy warning](https://mujoco.readthedocs.io/en/4.0.1/python.html#structs); [`Physics` state helpers](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py)
- `mj_forward(model,data)` computes the full forward dynamics without integrating time and makes `qacc`, actuator forces, mass matrix, bias, passive forces, and constraints consistent with current state/control. `mj_inverse(model,data)` requires the caller to set `qacc` and writes the required force to `qfrc_inverse`. — [main simulation API](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mainsimulation); [4.0.1 C header](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mujoco.h)
- Lower-level analytical helpers are also available: `mj_rne(..., flg_acc=1, result)` computes `M(q)qacc + C(q,qvel)` (and with `flg_acc=0`, only the bias term), `mj_mulM` multiplies by the inertia matrix, and `mj_solveM` solves an inertia system using MuJoCo's factorization. These do not by themselves apply the complete passive/constraint bookkeeping that makes `mj_inverse` the safer full-force oracle. — [`mj_rne`, `mj_mulM`, and `mj_solveM`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#sub-components)
- In `dm_control` 1.0.52 the wrapper calls are:

  ```python
  import mujoco

  m, d = env.physics.model, env.physics.data
  mujoco.mj_forward(m.ptr, d.ptr)

  d.qacc[:] = prescribed_qdd
  mujoco.mj_inverse(m.ptr, d.ptr)
  tau_required = d.qfrc_inverse.copy()
  ```

  For objects created natively with `mujoco.MjModel` and `mujoco.MjData`, call `mujoco.mj_forward(m, d)` and `mujoco.mj_inverse(m, d)` instead. — [`dm_control` migration guide](https://github.com/google-deepmind/dm_control/blob/1.0.52/migration_guide_1.0.md); [MuJoCo Python function mapping](https://mujoco.readthedocs.io/en/4.0.1/python.html#functions)
- On MuJoCo 4.0.1, obtain the dense mass matrix with:

  ```python
  M = np.empty((m.nv, m.nv), dtype=np.float64)
  mujoco.mj_fullM(m.ptr, d.ptr, M)  # dm_control wrappers
  # Native objects: mujoco.mj_fullM(m, d, M)
  ```

  Position-dependent dynamics must have been evaluated first, e.g. by `physics.forward()` or `mj_inverse`. — [`mj_fullM` 4.0.1 reference](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-fullm); [4.0.1 header signature](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mujoco.h)
- `qfrc_inverse` explicitly excludes passive force from its output: it is the net force that should equal actuator plus user-applied generalized/Cartesian forces. The inverse pipeline has already accounted for passive and constraint forces when solving the required applied force. — [`qfrc_inverse` header comment](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h); [inverse pipeline](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#inverse-dynamics)
- `mj_compareFwdInv` compares forward and inverse computations and writes solver diagnostics; enabling the `fwdinv` flag performs this check automatically. This is especially useful when constraints make forward dynamics a numerically terminated optimization while inverse dynamics remains analytical. — [`mj_compareFwdInv`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-comparefwdinv); [inverse solver discussion](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#inverse-dynamics)

#### Exact smooth two-link dynamics for the pinned model

- For states away from the wrist limit, with no user-applied forces, define `q=[q1,q2]`, `dq=[dq1,dq2]`, and these coefficients compiled from the pinned MJCF:

  ```text
  A = 9.7581009413152562e-4 kg·m²
  B = 2.7394687939302998e-4 kg·m²
  D = 1.8867358279909104e-4 kg·m²
  ```

  The dense inertia and bias are then

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
  \end{bmatrix},\qquad
  qfrc_{passive}=-0.01\dot q.
  \]

  Gravity torque is zero, so the required generalized actuator torque in the smooth interior is

  \[
  \tau_{act}=M(q)\ddot q+c(q,\dot q)+0.01\dot q=0.05u.
  \]

  These coefficients are a derivation from the pinned geometry/default density and were cross-checked against `mj_fullM`, `qfrc_bias`, and `qfrc_passive` on the 1.0.52/4.0.1 runtime. Treat them as a reproducibility assertion, not a substitute for querying the installed simulator. — [pinned reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [geom inertia inference](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#body-geom-density); [MuJoCo CRB/RNE definitions](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework)
- If the wrist limit is active, the complete required applied torque is instead

  \[
  \tau_{required}=M\ddot q+qfrc_{bias}-qfrc_{passive}-qfrc_{constraint},
  \]

  which is what `qfrc_inverse` returns when user-applied forces are zero. Omitting `qfrc_constraint` near the bound changes the learning target. — [MuJoCo inverse equation](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework); [`qfrc_constraint`/`qfrc_inverse`](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)

### Inferences

- For this fully actuated model, `qfrc_inverse` is the best authoritative oracle label for conventional joint torque. Mapping the result back to an original-environment command is simply `u=tau/0.05`, but only if every `|tau_i|<=0.05`; otherwise the prescribed acceleration is not realizable under the stock action bounds. — [reacher motor transmission](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [actuator transmission equation](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#transmission)
- The closed form is valuable as an independent test of indexing/sign conventions. The MuJoCo oracle remains authoritative if the XML changes because it automatically incorporates compiler-inferred inertias, passive forces, and constraints. — [MuJoCo `mj_inverse`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-inverse)

### Gaps

- MuJoCo 4.0.1's computation page still names `mjData.qM` in one notation table, while the 4.0.1 header/runtime expose `mjData.M` and the new `mj_fullM(model,data,dst)` signature. The header and runtime should control implementation; the stale `qM` mention is a documentation inconsistency. — [computation table](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework); [4.0.1 `mjData` header](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h); [4.0.1 `mj_fullM`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-fullm)
- The exact floating-point coefficients above are compiler outputs rather than stable public task constants. Recompute them from `model/data` in the reproduction environment. — [MuJoCo model compilation](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#parse-and-compile)

## How should leakage-free supervised tuples `(q, q_dot, q_ddot, tau)` be generated?

### Takeaway

Use one of two clearly named datasets: (1) **rollout-realized** tuples, where `qacc` and `qfrc_actuator` are captured at the same pre-integration state after `mj_forward`, or (2) **prescribed-oracle** tuples, where an analytic trajectory supplies coherent `q,q_dot,q_ddot` and `mj_inverse` supplies the required generalized torque. Never pair desired acceleration with saturated realized torque, and never read post-step `qpos/qvel` alongside stale pre-step `qacc`. — [MuJoCo forward/inverse API](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mainsimulation); [`dm_control.Physics.step`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py)

### Cited Findings

#### Workflow A: realized forward-dynamics tuples

- `control.Environment.step` sets the action, advances physics, then returns the post-step observation. In the current default `legacy_step=True` path, `dm_control.Physics.step` finishes integration and calls `mj_step1` on the **new** state to refresh position/velocity-dependent fields; acceleration-dependent fields are not recomputed. Therefore, immediately after a step, `qpos/qvel` are at `t+h` while `qacc` is the acceleration used at the previous state. — [`Environment.step`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py); [`Physics._step_with_up_to_date_position_velocity`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py); [`mj_step1`/`mj_step2`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mainsimulation)
- The robust sequence is: set the action, call `physics.forward()` without integration, copy all fields, and only then step. The following is valid for the pinned 4.0.1 API: — [`Physics.forward`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py); [`mj_forward`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-forward)

  ```python
  import numpy as np
  import mujoco

  def realized_sample_then_step(physics, action):
      m, d = physics.model, physics.data

      physics.set_control(np.asarray(action, dtype=np.float64))
      physics.forward()  # synchronize qacc and all force terms at (q, dq, u)

      M = np.empty((m.nv, m.nv), dtype=np.float64)
      mujoco.mj_fullM(m.ptr, d.ptr, M)  # MuJoCo 4.0.x signature

      sample = {
          "time": float(d.time),
          "q": d.qpos.copy(),
          "q_dot": d.qvel.copy(),
          "q_ddot_realized": d.qacc.copy(),
          "u": d.ctrl.copy(),
          "actuator_force": d.actuator_force.copy(),
          "tau_actuator": d.qfrc_actuator.copy(),
          "qfrc_bias": d.qfrc_bias.copy(),
          "qfrc_passive": d.qfrc_passive.copy(),
          "qfrc_constraint": d.qfrc_constraint.copy(),
          "M": M.copy(),
          "nefc": int(d.nefc),
      }

      physics.step()  # integrate only after copying the synchronized tuple
      return sample
  ```

- Calling low-level `physics.step()` does not update the environment's private step counter, reward, or termination. That is acceptable for a dynamics-only collector; if dm_env episode semantics are needed, capture the synchronized tuple in a custom task's `before_step` hook and let `env.step` continue normally. — [`control.Environment.step`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py); [`base.Task.before_step`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/base.py)
- Do not estimate continuous `q_ddot` as `(qvel[t+1]-qvel[t])/0.02` for this model. Default Euler handles joint damping implicitly, so the finite velocity increment does not in general equal the continuous acceleration stored by forward dynamics. The `invdiscrete` option exists for deliberately interpreting finite-difference accelerations under supported integrators, but that is a different target definition. — [Euler integration and implicit damping](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#integrators); [`invdiscrete` flag](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#option-flag-invdiscrete)
- If `environment_kwargs` changes control timestep or action repeats, one control can span several physics states. Per-physics-step dynamics data then require logging each substep rather than only one aggregate control transition. The stock reacher has one substep. — [`control.Environment` timestep logic](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py)

#### Workflow B: prescribed kinematics with analytical inverse labels

- For trajectory tracking, construct differentiable joint trajectories and evaluate `q(t)`, `q_dot(t)`, and `q_ddot(t)` analytically at the same timestamps (e.g., phase-randomized sums of sinusoids or boundary-conditioned quintic splines). This avoids differencing noise, filtering lag, and cross-split derivatives. MuJoCo explicitly describes inverse dynamics as mapping prescribed position, velocity, and acceleration to applied force. — [inverse-dynamics purpose](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#inverse-dynamics-and-optimization); [`mj_inverse`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-inverse)
- Use a copied `Physics`/`MjData` so oracle calls cannot perturb a rollout collector. Set all external forces to zero, prescribe the three kinematic arrays, call inverse, and copy its output: — [`Physics.copy`](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py); [`mj_inverse`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-inverse)

  ```python
  import numpy as np
  import mujoco

  oracle = env.physics.copy(share_model=True)

  def inverse_oracle(q, q_dot, q_ddot):
      m, d = oracle.model, oracle.data
      d.qpos[:] = np.asarray(q, dtype=np.float64)
      d.qvel[:] = np.asarray(q_dot, dtype=np.float64)
      d.qacc[:] = np.asarray(q_ddot, dtype=np.float64)
      d.ctrl[:] = 0.0                  # not an input to inverse dynamics
      d.qfrc_applied[:] = 0.0
      d.xfrc_applied[:] = 0.0

      mujoco.mj_inverse(m.ptr, d.ptr)

      M = np.empty((m.nv, m.nv), dtype=np.float64)
      mujoco.mj_fullM(m.ptr, d.ptr, M)
      return {
          "q": d.qpos.copy(),
          "q_dot": d.qvel.copy(),
          "q_ddot_prescribed": d.qacc.copy(),
          "tau_required": d.qfrc_inverse.copy(),
          "qfrc_bias": d.qfrc_bias.copy(),
          "qfrc_passive": d.qfrc_passive.copy(),
          "qfrc_constraint": d.qfrc_constraint.copy(),
          "M": M.copy(),
          "nefc": int(d.nefc),
      }
  ```

- A coherent desired trajectory can still be dynamically infeasible. Mark or reject samples for which `abs(tau_required)>0.05` N·m, because replay would require controls outside `[-1,1]`. Never clip the torque and keep the original prescribed acceleration as though it were realized. — [stock control/gear bounds](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [control clamping](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#option-flag-clampctrl)
- To learn the smooth rigid-body map, keep the wrist trajectory safely inside `[-2.7925,2.7925]` rad (for example, use a documented margin such as `|q2|<=2.6`) and reject any row with significant `qfrc_constraint` or active limit rows. If constrained inverse dynamics is intentionally in scope, retain `qfrc_constraint`, constraint status, and a separate evaluation stratum instead of mixing it silently with smooth samples. — [wrist range](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo constraint fields](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)

#### Label and split rules

- Recommended canonical row schema:

  ```text
  trajectory_id, episode_id, seed, t,
  q[2], q_dot[2], q_ddot[2], tau_joint[2],
  ctrl[2] (if a rollout), actuator_force[2] (if a rollout),
  qfrc_bias[2], qfrc_passive[2], qfrc_constraint[2],
  nefc, feasible, source={realized|prescribed},
  dm_control_version, mujoco_version, xml_sha256,
  physics_timestep, control_timestep, integrator, legacy_step
  ```

  Keeping command, output-space force, and joint-space torque as separate named columns prevents actuator/generalized-force confusion. — [MuJoCo actuation spaces](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model); [integration state and determinism](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#state)
- Split train/validation/test by complete `trajectory_id` or episode/seed **before** fitting normalization. Never randomly split adjacent rows from the same trajectory; they are strongly correlated and can make interpolation look like generalization. If any numerical derivative were unavoidable, compute it wholly within a split and discard boundary points so a test sample is never used to construct a training feature/label. This is a methodological inference from the trajectory sampling process, not a dm_control API behavior. — [MuJoCo trajectory-state determinism](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#reproducibility)
- Store `.copy()` results immediately. Appending raw `data.qpos`, slices, or other MuJoCo arrays stores aliases that update in-place on later simulation calls and can silently make all dataset rows equal to the latest state. — [MuJoCo Python zero-copy warning](https://mujoco.readthedocs.io/en/4.0.1/python.html#structs)
- For rollout coverage, use seeded, bounded, band-limited/persistently exciting controls rather than independent high-frequency full-scale actions at every 20 ms step; the links have very small inertias and full-scale switching quickly drives the wrist into its limit. Record the excitation process and seed. This is an experiment-design inference grounded in the stock torque bounds/inertias. — [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [compiled-inertia mechanism](https://mujoco.readthedocs.io/en/4.0.1/XMLreference.html#body-geom-density)

### Inferences

- The prescribed-oracle dataset is best for testing whether a network can learn the exact inverse map over a designed state domain; the rollout-realized dataset is best for testing what the stock bounded actuators actually visit. Maintaining both, with separate source labels and trajectory-level splits, avoids conflating function approximation with controller visitation. — [MuJoCo forward/inverse mapping](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mainsimulation)
- Desired `q_ddot_d` belongs in a tuple only when `mj_inverse` computes its required torque. During closed-loop rollout, the tuple must contain realized `data.qacc`; desired acceleration can be stored as an additional controller reference, never substituted for realized acceleration. — [forward versus inverse definitions](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mainsimulation)

### Gaps

- The project's intended distribution over trajectories, velocities, accelerations, and actuator feasibility was not specified. It must be declared before dataset generation so oracle/test coverage is reproducible.
- The project must choose whether limit dynamics are excluded, modeled as a separate regime, or included in one discontinuous/constraint-aware target. The stock simulator supports them, but a smooth two-link analytical model does not include them unless `qfrc_constraint` is added. — [MuJoCo constraint dynamics](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#constraint)

## How should MuJoCo analytical dynamics be used as an oracle baseline?

### Takeaway

Compare a learned model to `qfrc_inverse` in generalized-force space, then separately test equation residuals, acceleration consistency, actuator-feasible rollout, and tracking performance. Comparing network output directly to `ctrl` or `actuator_force` without the `0.05` transmission is a unit/space error. — [`qfrc_inverse` semantics](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h); [actuator transmission](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#transmission)

### Cited Findings

- **Primary supervised comparison:** for each held-out tuple, compare `tau_hat(q,dq,ddq)` with `tau_oracle=data.qfrc_inverse`. Report per-joint and aggregate MAE/RMSE, a normalized error using training-set torque scale, maximum/percentile errors, and errors stratified by `q2`, speed, acceleration, and torque-feasibility. The oracle field is the force output of MuJoCo inverse dynamics. — [`mj_inverse` and `qfrc_inverse`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-inverse); [`mjData` output definition](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)
- **Physics residual:** with no external applied force, evaluate

  \[
  r=M(q)\ddot q+qfrc_{bias}-qfrc_{passive}-qfrc_{constraint}-\hat\tau.
  \]

  Report `||r||` and each component. Substituting `tau_oracle` should reduce this residual to floating-point/solver tolerance and is an end-to-end sign/index check. — [MuJoCo equations](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework); [`mjData` force fields](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)
- **Forward-acceleration comparison:** for feasible predictions, map `u_hat=tau_hat/0.05`, call `mj_forward` at the held-out `(q,dq,u_hat)`, and compare the resulting `qacc_hat` with prescribed/held-out `qddot`. This measures the physical effect of torque error in a coupled, configuration-dependent system. — [reacher actuator gear](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [`mj_forward`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-forward)
- **Forward/inverse self-check:** take a synchronized forward tuple, save its `qacc` and `qfrc_actuator`, call `mj_inverse` with that same `qacc`, and verify `qfrc_inverse≈qfrc_actuator` when external forces are zero. `mj_compareFwdInv` or the `fwdinv` flag formalizes the same consistency check, particularly when constraints are active. — [`mj_compareFwdInv`](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-comparefwdinv); [inverse-dynamics solver check](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#inverse-dynamics)
- **Closed-loop rollout comparison:** apply the learned inverse term inside the same feedback controller and compare joint tracking RMSE, peak error, torque saturation fraction, limit activations, and long-horizon divergence with (a) MuJoCo-oracle feedforward, (b) feedback-only, and (c) the learned feedforward model. Keep controller gains, reference trajectories, integration settings, and initial states identical. This is an experimental inference built on the stock dynamics/control API. — [`control.Environment` stepping](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py); [MuJoCo deterministic pipeline](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#reproducibility)
- The analytical oracle is not a noisy measurement baseline: on the same MuJoCo model it encodes the simulator's own ground-truth equations. Its near-zero torque error is therefore a correctness ceiling; learned-model value comes from approximation, inductive bias, data efficiency, speed, robustness, or transfer—not from outperforming the simulator on its own labels. — [MuJoCo inverse-dynamics design](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#inverse-dynamics-and-optimization)
- Keep these comparison spaces explicit:

  | Comparison | Correct reference |
  |---|---|
  | learned generalized torque | `qfrc_inverse` or synchronized `qfrc_actuator` |
  | policy/action prediction | `ctrl`, after documenting normalization/range |
  | actuator-output prediction | `actuator_force` |
  | dynamics decomposition | `M`, `qfrc_bias`, `qfrc_passive`, `qfrc_constraint` |
  | realized acceleration | synchronized pre-step `qacc` |

  MuJoCo documents these as distinct spaces and fields. — [actuation model](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model); [`mjData` definitions](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)

### Inferences

- A useful acceptance test for the complete data pipeline is to require three simultaneous identities on interior samples: `qfrc_actuator≈0.05*ctrl`, `qfrc_inverse≈qfrc_actuator` after feeding forward `qacc` into inverse, and `qfrc_inverse≈M@qacc+qfrc_bias-qfrc_passive`. Any failure points directly to control clipping, temporal misalignment, an active constraint, an external force, or a version/sign error. — [reacher transmission](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml); [MuJoCo equations and inverse output](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#general-framework)
- Report constrained/limit samples separately even if the final model includes them; otherwise a small number of high-force boundary rows can dominate aggregate torque metrics and obscure smooth interior performance. — [MuJoCo limit constraints](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APItypes.html#mjtconstraint)

### Gaps

- No target model architecture, loss normalization, trajectory family, or success threshold was supplied, so exact benchmark tolerances cannot be prescribed here.
- Oracle wall-clock comparisons depend on batching, Python overhead, device, and whether the learned model runs on CPU/GPU. They require a controlled benchmark rather than an API-level claim.

## What is version-sensitive as of November 2026, and which sources/examples matter?

### Takeaway

The current reproducibility stack is dm_control 1.0.52 + MuJoCo 4.0.1. The main breaking detail for this project is MuJoCo 4's mass-matrix storage/call signature; older examples using `data.qM` are not source-compatible. Pin versions, inspect signatures at runtime, and cite tag-specific source rather than `main`/`stable`. — [dm_control 1.0.52 release](https://github.com/google-deepmind/dm_control/releases/tag/1.0.52); [MuJoCo 4.0.1 changelog](https://mujoco.readthedocs.io/en/4.0.1/changelog.html#version-4-0-1-november-11-2026)

### Cited Findings

#### Version-sensitive API differences

- `dm_control` 1.0.52 declares Python `>=3.9` and MuJoCo `>=4.0.1`, but MuJoCo 4.0.0 removed Python 3.10 support. Therefore the dm_control lower-bound metadata alone is insufficient to guarantee an installable MuJoCo wheel; verify the exact interpreter/platform wheel before freezing the environment. — [dm_control 1.0.52 package metadata](https://pypi.org/project/dm-control/1.0.52/); [MuJoCo 4.0.0 Python change](https://mujoco.readthedocs.io/en/4.0.1/changelog.html#version-4-0-0-november-6-2026)
- Since dm_control 1.0, advanced calls should use the official top-level `mujoco` module. With a `dm_control.Physics`, pass wrapper pointers (`model.ptr`, `data.ptr`); with native MuJoCo Python structs, pass objects directly. Older pre-1.0 examples based on `dm_control.mujoco.wrapper.mjbindings.mjlib` are legacy. — [`dm_control` 1.0 migration guide](https://github.com/google-deepmind/dm_control/blob/1.0.52/migration_guide_1.0.md); [MuJoCo native Python bindings](https://mujoco.readthedocs.io/en/4.0.1/python.html)
- MuJoCo 3.3.7 used `mj_fullM(model, dst, data.qM)` and documented `qM` as its custom sparse inertia representation. MuJoCo 4.0.1 uses `mj_fullM(model, data, dst)` and its header exposes sparse `data.M`, not `data.qM`. Code should branch on the installed version/signature rather than guess. — [`mj_fullM` 3.3.7](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-fullm); [`mj_fullM` 4.0.1](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html#mj-fullm); [4.0.1 `mjData`](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)
- Current MuJoCo allows controls, actuator force outputs, and actuators to have different counts (`nu`, `nout`, `nactuator`). The reacher remains ordinary SISO with all equal to 2, but generic extraction code should use each field's actual shape. — [current actuation model](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#actuation-model); [current `mjData`](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h)
- MuJoCo's `discrete` integrator was new in September 2026 and changes `qacc` to mean the finite-step velocity map `(v_next-v)/h`; it is explicitly described as under active development. The stock reacher remains on default Euler, where forward/inverse dynamics use continuous acceleration, unless the XML/options are modified. — [MuJoCo 4.0.1 integrators](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#integrators); [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)
- MuJoCo 4.0.1 fixed a sparse Cholesky/Newton-solver bug introduced in 4.0.0 that could produce wrong accelerations/divergence. Even though this tiny reacher normally has dense smooth dynamics and contacts disabled, 4.0.1—not 4.0.0—is the appropriate November 2026 pin. — [MuJoCo 4.0.1 bug fix](https://mujoco.readthedocs.io/en/4.0.1/changelog.html#version-4-0-1-november-11-2026)

#### Runtime verification checklist

- Run the following immediately after installation and archive its output with the dataset. Every asserted value is expected for the pinned stack but intentionally treated as runtime-verifiable rather than timeless. — [reacher source](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py); [reacher MJCF](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml)

  ```python
  import hashlib
  import importlib.metadata as md
  import numpy as np
  import mujoco
  from dm_control import suite
  from dm_control.suite import reacher

  print("dm-control", md.version("dm-control"))
  print("mujoco", mujoco.__version__, mujoco.mj_versionString())

  xml, _ = reacher.get_model_and_assets()
  print("reacher_xml_sha256", hashlib.sha256(xml.encode()).hexdigest())

  env = suite.load("reacher", "easy", task_kwargs={"random": 0})
  first = env.reset()
  m, d = env.physics.model, env.physics.data

  print("observation_spec", env.observation_spec())
  print("action_spec", env.action_spec())
  print("nq nv nu na", m.nq, m.nv, m.nu, m.na)
  print("physics_dt", env.physics.timestep())
  print("control_dt", env.control_timestep())
  print("integrator", m.opt.integrator)
  print("joint_range", m.jnt_range.copy())
  print("ctrl_range", m.actuator_ctrlrange.copy())
  print("gear", m.actuator_gear.copy())
  print("has_qM", hasattr(d, "qM"), "has_M", hasattr(d, "M"))
  print("mj_fullM_signature", mujoco.mj_fullM.__doc__.splitlines()[0])

  assert (m.nq, m.nv, m.nu, m.na) == (2, 2, 2, 0)
  assert env.physics.timestep() == 0.02
  assert env.control_timestep() == 0.02
  assert tuple(first.observation) == ("position", "to_target", "velocity")
  assert env.action_spec().shape == (2,)
  assert np.allclose(m.actuator_ctrlrange, [[-1, 1], [-1, 1]])

  env.physics.set_control([0.4, -0.6])
  env.physics.forward()
  assert np.allclose(d.qfrc_actuator, [0.02, -0.03])
  ```

#### Primary source and example map

| Purpose | Authoritative source |
|---|---|
| exact task factory, observation, target randomization, reward | [`dm_control/suite/reacher.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.py) |
| bodies, geoms, joints, damping, motors, gear, bounds, physics dt | [`dm_control/suite/reacher.xml` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/reacher.xml) |
| action-to-control behavior | [`dm_control/suite/base.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/base.py) |
| environment stepping, action repeats, control dt, time limit | [`dm_control/rl/control.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/rl/control.py) |
| direct state methods and legacy stepping synchronization | [`dm_control/mujoco/engine.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/mujoco/engine.py) |
| reset joint distribution | [`suite/utils/randomizers.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/suite/utils/randomizers.py) |
| sparse reward semantics | [`dm_control/utils/rewards.py` at 1.0.52](https://github.com/google-deepmind/dm_control/blob/1.0.52/dm_control/utils/rewards.py) |
| dm_control API introduction / named access / suite examples | [official `dm_control` tutorial notebook](https://github.com/google-deepmind/dm_control/blob/1.0.52/tutorial.ipynb) |
| native Python object/array semantics | [MuJoCo 4.0.1 Python docs](https://mujoco.readthedocs.io/en/4.0.1/python.html) and [official MuJoCo tutorial](https://github.com/google-deepmind/mujoco/blob/4.0.1/python/tutorial.ipynb) |
| equations, actuation, integration, forward/inverse pipeline | [MuJoCo 4.0.1 computation chapter](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html) |
| callable dynamics API (`mj_forward`, `mj_inverse`, `mj_fullM`) | [MuJoCo 4.0.1 function reference](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APIfunctions.html) and [`mujoco.h` tag 4.0.1](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mujoco.h) |
| exact field meanings | [MuJoCo 4.0.1 type reference](https://mujoco.readthedocs.io/en/4.0.1/APIreference/APItypes.html#mjdata) and [`mjdata.h` tag 4.0.1](https://github.com/google-deepmind/mujoco/blob/4.0.1/include/mujoco/mjdata.h) |
| pre-1.0 to official binding migration | [`dm_control` migration guide](https://github.com/google-deepmind/dm_control/blob/1.0.52/migration_guide_1.0.md) |
| release-specific behavior/fixes | [dm_control releases](https://github.com/google-deepmind/dm_control/releases) and [MuJoCo changelog](https://mujoco.readthedocs.io/en/4.0.1/changelog.html) |

### Inferences

- A hermetic reproduction record should include the exact wheel versions, Python/platform, XML SHA-256, seed, compiled model dump or the key arrays above, dataset-generation commit, and serialized configuration. A version number alone is insufficient when dm_control's MuJoCo requirement is open-ended (`>=4.0.1`). — [dm_control package requirement](https://pypi.org/project/dm-control/1.0.52/); [MuJoCo reproducibility notes](https://mujoco.readthedocs.io/en/4.0.1/computation/index.html#reproducibility)
- Use versioned documentation URLs (`/en/4.0.1/`) and Git tags (`/blob/1.0.52/`) in the report. `stable` and `main` can move after the experiment and can silently change signatures or constants. — [MuJoCo changelog](https://mujoco.readthedocs.io/en/4.0.1/changelog.html); [dm_control releases](https://github.com/google-deepmind/dm_control/releases)

### Gaps

- Official package metadata and MuJoCo's Python support statement are not expressed as one consistent interpreter range: dm_control says Python `>=3.9`, while MuJoCo 4.0 removed 3.10. The exact supported wheel set should be verified on PyPI/CI for the deployment platform rather than inferred. — [dm_control PyPI metadata](https://pypi.org/project/dm-control/1.0.52/); [MuJoCo 4.0 changelog](https://mujoco.readthedocs.io/en/4.0.1/changelog.html#version-4-0-0-november-6-2026)
- The project has not specified whether it must reproduce an older university environment lockfile. If one exists, its pinned dm_control/MuJoCo versions take precedence, and the 3.x/4.x mass-matrix branch must match that lockfile.
