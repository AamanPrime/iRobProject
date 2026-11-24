# Physics-Informed Inverse Dynamics for Reacher Arm Tracking

## Project in one sentence

This project teaches a neural network how much torque a two-joint robot arm needs to follow a desired movement, then compares a **physics-informed network** with a normal neural network and MuJoCo's exact physics model.

## The idea in simple terms

Imagine moving your arm to pick up a cup. Your brain does not only decide where your hand should go. It also decides how strongly each muscle should pull while accounting for:

- the weight and inertia of your arm;
- the interaction between your shoulder and elbow;
- how fast your arm is already moving;
- friction and resistance in the joints.

A robot has the same basic problem. It needs the correct torque at each joint to create the desired acceleration.

This relationship is called **inverse dynamics**:

```text
joint angles + joint velocities + desired accelerations
                         ↓
                  inverse dynamics
                         ↓
                 required joint torques
```

Mathematically, the project learns:

```text
(q, q_dot, q_ddot) → tau
```

where:

- `q` means the two joint angles;
- `q_dot` means the two joint velocities;
- `q_ddot` means the desired joint accelerations;
- `tau` means the two required joint torques.

## What robot will be used?

The project uses the `reacher/easy` robot from DeepMind's `dm_control` package. It is a simulated arm with:

- two rotating joints: shoulder and wrist;
- two directly controlled motors;
- two links moving on a flat horizontal plane;
- a 50 Hz simulation and control rate;
- a maximum joint torque of `±0.05 N·m` per joint.

The original `reacher/easy` task asks the fingertip to touch a target. This project reuses the same robot physics but creates a new task: **following a changing joint-space trajectory over time**.

## What will the project build?

### 1. A data generator

The project will generate many smooth arm movements. For every moment in a movement, it will store:

- current joint angles;
- current joint velocities;
- desired joint accelerations;
- required joint torques calculated by MuJoCo.

The data will be divided by complete trajectories into training, validation, normal test, and out-of-range test sets.

### 2. A physics-informed Lagrangian neural network

This network will not learn the torque relationship as an unrestricted black box. It will learn physically meaningful parts of the arm model, including:

- the configuration-dependent mass or inertia matrix;
- Coriolis and centrifugal coupling between the joints;
- potential-energy effects;
- viscous joint damping.

The Euler–Lagrange equation will combine these learned parts to calculate torque. The learned mass matrix will be positive definite by construction, which prevents physically invalid negative kinetic energy.

This model is referred to as a **DeLaN-style Lagrangian neural network**.

### 3. A normal black-box neural network

The black-box model will receive the same inputs and training records but will predict torque directly:

```text
angles + velocities + accelerations → MLP → torques
```

It will not be told the equations of robot mechanics. Comparing it with the Lagrangian model will show whether adding physics helps when only limited training data are available.

### 4. An analytical MuJoCo baseline

MuJoCo already knows the exact simulated robot model. Its inverse-dynamics calculation will be used as the ground-truth analytical baseline.

This baseline answers an important question:

> How close do the learned models come to the simulator's exact dynamics?

### 5. A computed-torque controller

The trained inverse models will be placed inside a feedback controller. At each control step, the controller will:

1. read the current joint angles and velocities;
2. compare them with the desired trajectory;
3. calculate a corrected desired acceleration;
4. ask the selected inverse model for the required torques;
5. apply the torques to the simulated arm;
6. repeat the process 50 times per second.

The basic controller is:

```text
corrected acceleration = desired acceleration
                       + position correction
                       + velocity correction

joint torque = inverse_model(
    current angles,
    current velocities,
    corrected acceleration
)
```

## Models being compared

| Model | Uses learned physics structure? | Predicts torque? | Used for tracking? |
|---|:---:|:---:|:---:|
| MuJoCo analytical model | Exact simulator physics | Yes | Yes |
| Lagrangian/DeLaN model | Yes | Yes | Yes |
| Black-box inverse MLP | No | Yes | Yes |
| Optional feedback-only controller | No inverse model | No | Yes |

A separate black-box forward model will be trained from the same records for the open-loop rollout comparison. The Lagrangian model can calculate both inverse and forward dynamics from one shared physical representation.

## How will the experiment work?

### Step 1: Generate ground-truth data

Smooth reference trajectories will provide exact angles, velocities, and accelerations. MuJoCo inverse dynamics will provide the matching torques.

### Step 2: Train with different amounts of data

Both learned inverse models will be trained using:

- 10% of the training trajectories;
- 30% of the training trajectories;
- 100% of the training trajectories.

This will test **data efficiency**: whether the physics-informed model can learn a useful dynamics model from fewer examples.

### Step 3: Test normal prediction

The models will predict torque for new movements that remain inside the training range.

### Step 4: Test generalization

The models will also be tested at joint configurations outside the training range but still safely inside the robot's physical limits.

This tests whether a model learned the underlying mechanics or only memorized familiar examples.

### Step 5: Run two-second open-loop rollouts

Each forward model will start from the same state and receive the same torque sequence for two seconds. Its predicted motion will be compared with the analytical motion.

This reveals how small one-step errors accumulate over time.

### Step 6: Run closed-loop tracking trials

The analytical, Lagrangian, and black-box inverse models will each control the arm using:

- the same reference trajectories;
- the same starting states;
- the same feedback gains;
- the same torque limits;
- the same simulation timestep.

At least 10 fixed trials will be evaluated for every required condition.

## How will success be measured?

### Inverse-dynamics accuracy

- torque root mean squared error (RMSE);
- torque mean absolute error (MAE);
- error for each joint;
- large-error and 95th-percentile behavior;
- normal versus out-of-range error.

### Two-second rollout accuracy

- joint-angle RMSE;
- joint-velocity RMSE;
- final-state error;
- divergence or invalid-prediction rate.

### Closed-loop tracking

- joint tracking RMSE;
- fingertip-position RMSE;
- maximum and final tracking error;
- successful trials out of 10;
- torque saturation percentage;
- joint-limit activations;
- controller inference time.

### Data efficiency

Results from 10%, 30%, and 100% training data will be plotted together. This will show how quickly each model improves as more data become available.

## Why is this useful?

Accurate inverse dynamics helps a robot move quickly and precisely without depending entirely on very strong feedback corrections. A learned model can also compensate for dynamics that are unknown, difficult to measure, or changing over time.

Physics-informed learning is useful because it tries to combine two strengths:

- **robotics equations** provide physically meaningful structure;
- **neural networks** learn unknown values and relationships from data.

The goal is not simply to obtain a low test loss. The learned model must remain useful when placed inside a real feedback loop.

## Real-world examples

### Industrial robot arms

A welding, painting, or assembly robot must follow the same path accurately thousands of times. Better inverse dynamics can reduce tracking error at higher movement speeds.

### Pick-and-place systems

When a robot repeatedly moves products between a conveyor and a container, accurate torque prediction can make its motion faster and smoother while reducing overshoot.

### Robots carrying changing payloads

A warehouse arm may pick up objects with different masses. A learned dynamics model can be retrained or adapted from recorded motion instead of requiring every physical parameter to be measured manually.

### Collaborative robots

Collaborative arms often use lower feedback gains to remain compliant around people. Accurate feedforward torque helps them track well without becoming unnecessarily stiff.

### Rehabilitation and assistive robots

An exoskeleton must calculate how much joint torque to provide while its configuration and movement speed change. Physics-informed learning can help model the combined mechanism more efficiently from limited measurements.

### Drones, walking robots, and autonomous vehicles

Although this project uses a two-joint arm, the same idea applies whenever a controller needs a dynamics model. Examples include predicting forces for drone motion, leg torques for walking, or steering and tire forces for a vehicle.

### Digital twins and predictive maintenance

A learned dynamics model can act as a compact digital twin. Increasing disagreement between predicted and observed torque may indicate friction changes, wear, damage, or an unexpected payload.

## Expected result

The expected hypothesis is that the physics-informed model will be especially useful with 10% and 30% of the data and when tested outside the training range. The black-box network may become competitive when enough representative data are available.

This is a hypothesis, not a guaranteed result. A carefully measured negative result is still meaningful—for example, if the Lagrangian model improves torque prediction but does not improve tracking, the project will investigate feedback gains, saturation, conditioning, and rollout error to explain why.

## Important limitations

- This is a simulation study, not a hardware experiment.
- The arm moves horizontally, so gravity produces no joint torque.
- Contacts are disabled in the primary experiment.
- The main tests avoid the wrist joint limit.
- Results from a two-joint arm do not automatically prove performance on large industrial robots.
- Positive-definite learned inertia does not by itself guarantee stable tracking.

## Planned project outputs

- reproducible dataset generator;
- analytical MuJoCo inverse-dynamics interface;
- Lagrangian and black-box models;
- computed-torque controller;
- automated tests;
- saved model checkpoints;
- learning curves and comparison tables;
- rollout and tracking plots;
- example simulation videos;
- final course report and presentation material.

## Current status

- [x] Topic interpretation and requirements analysis
- [x] `dm_control` and MuJoCo dynamics research
- [x] Lagrangian-network and inverse-dynamics literature review
- [x] Experiment and evaluation protocol
- [ ] Environment setup and runtime model verification
- [ ] Dataset implementation
- [ ] Model implementation
- [ ] Training and evaluation
- [ ] Closed-loop controller and demo
- [ ] Final report and presentation

## Detailed technical documentation

The complete technical specification is available in:

- [`reports/Reacher inverse dynamics requirements.md`](reports/Reacher%20inverse%20dynamics%20requirements.md)
- [`research_notes/Physics informed reacher inverse dynamics/dm_control_and_mujoco.md`](research_notes/Physics%20informed%20reacher%20inverse%20dynamics/dm_control_and_mujoco.md)
- [`research_notes/Physics informed reacher inverse dynamics/literature_and_code.md`](research_notes/Physics%20informed%20reacher%20inverse%20dynamics/literature_and_code.md)
- [`research_notes/Reacher inverse dynamics requirements/source_addendum.md`](research_notes/Reacher%20inverse%20dynamics%20requirements/source_addendum.md)

Installation and execution commands will be added after the implementation environment and command-line interfaces are finalized.
