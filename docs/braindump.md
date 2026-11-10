# Holy Guacamole — Full Project Braindump

> **Superseded for hardware by [`spec.md`](spec.md) (rev 2).** This braindump describes the Rev A carrier (JLCPCB, 2 layers, SK9822 status LEDs, on-board receiver). Treat its PCB sections as history; the rev 2 board, pin map and fab rules live in `spec.md`.
 
**Robot:** Holy Guacamole — 1lb meltybrain antweight, MRCA full-combat ruleset  
**Document type:** Running knowledge dump — research, design decisions, hardware, firmware architecture  
**Target event:** none set (Buckeye Bot Bash 2, Aug 29 2026, has passed)  
**Status:** Chassis v3.4f and the rev 2 carrier (routed for PCBWay) are designed. Next: the MJF frame, the PCB order, and bench bring-up. Hardware numbers here are refreshed to v3.4f; `spec.md` (Rev B 2.1) is the authority where they differ.
 
---
 
## Table of Contents
 
1. [What is a meltybrain](#1-what-is-a-meltybrain)
2. [Robot concept and goals](#2-robot-concept-and-goals)
3. [Ruleset constraints](#3-ruleset-constraints-mrca-full-antweight)
4. [Chassis design](#4-chassis-design)
5. [Operating parameters](#5-operating-parameters)
6. [Control theory research](#6-control-theory-research)
7. [Community RPM data and operating insights](#7-community-rpm-data-and-operating-insights)
8. [IMU placement — design evolution](#8-imu-placement--design-evolution)
9. [Electronics hardware](#9-electronics-hardware)
10. [Carrier PCB specification](#10-carrier-pcb-specification)
11. [Firmware architecture](#11-firmware-architecture)
12. [Mass budget](#12-mass-budget)
13. [Event calendar](#13-event-calendar)
14. [Reference builds](#14-reference-builds)
15. [Open questions](#15-open-questions)
---
 
## 1. What is a meltybrain
 
A meltybrain (also called translational drift) robot is a full-body spinner where the entire chassis rotates using its drive wheels as the weapon. Unlike a standard full-body spinner which uses a separate high-speed motor for the weapon, a meltybrain uses the drive motors themselves to spin the body. Directional control is achieved by modulating motor power at precise angular positions each revolution — effectively vectoring thrust by knowing exactly where the robot is pointing at any instant.
 
The key challenge: the robot has no static reference frame. It is spinning continuously at thousands of RPM. The control system must maintain a real-time estimate of chassis heading (0–360°) derived entirely from onboard sensors, and use that heading to decide which motor to power and when. Without accurate heading, the robot either cannot translate (no directionality) or worse, translates in the wrong direction.
 
This is fundamentally a state estimation problem wrapped around a control problem, not just a drive problem.
 
### Why it's interesting
 
A well-tuned meltybrain is simultaneously a full-body spinner (kinetic energy in the rotating mass) and a controlled mobile robot. The chassis IS the weapon. At 4,000 RPM the tooth tips (r 90 mm) move at ~84 mph and the body stores ~120 J. With a steel ring, this is a meaningful combat machine.
 
The autonomous sensing extension (Holy Guacamole II) exploits the spinning geometry in a novel way: IR sensors spinning at 4,000 RPM scan the arena 67 times per second, building a polar reflectance map that can locate opponents without any external tracking infrastructure. This is impossible on a stationary robot and is one of the genuinely novel things this platform enables.
 
---
 
## 2. Robot concept and goals
 
**Name:** Holy Guacamole  
"Holy Guacamole" — chaotic energy, memorable pit presence.
"II" implies a lineage. Holy Guacamole II adds opponent sensing, most likely a spinning IR lidar.
 
**Design philosophy:**
- Holy Guacamole is a proof-of-platform. Manual RC control, validate the heading algorithm, prove the mechanical design survives combat.
- Holy Guacamole II upgrades the IMU fusion algorithm and adds opponent detection.
- Data-driven redesign after v1: the PLA+ v1 chassis worked okay-ish but shattered, its weapon tabs broke out of their pockets, and it was too heavy. v3.x is sized from FEA, modal and fit checks.

**Combat strategy:**
- Spin up to tracking RPM before engaging, punch to strike RPM on contact
- Translate toward opponent using drift control
- Two-tooth steel ring; motors on the E/W axis, perpendicular to the teeth
- Full invertibility — symmetric top/bottom design means being flipped is not a loss condition
 
---

## 3. Ruleset constraints (MRCA full antweight)
 
| Rule | Detail |
|---|---|
| Weight limit | 1.00 lb / 454g for wheeled robots |
| Materials | No restrictions — metal, UHMW, Delrin, carbon fiber all permitted |
| Active weapon | Meltybrain legality must be confirmed with each event organizer. MRCA ruleset lists "rolling (wheels, tracks, or the whole robot)" as permitted mobility and does not explicitly ban translational drift. **Confirm with the EO of each event before entering.** |
| Spindown | Full stop within 60 seconds of power removal, self-contained braking. Active ESC braking satisfies this. |
| Failsafe | Radio must failsafe all motion (drive + weapon) on signal loss |
| Battery | LiPo permitted. Must be fully enclosed. Uncontained battery = automatic KO. |
| Arena | MDF floor, ¼" polycarbonate walls, ~6×6ft nominal |
| Match duration | 2 minutes |
| Pinning limit | 5 seconds max |
 
**Key note:** This is full-combat antweight, NOT plastic ant. Steel weapons, UHMW chassis reinforcement, and carbon fiber are all permitted. Design accordingly.
 
---
 
## 4. Chassis design (v3.4f)

The chassis comes from the v3.4f CAD (the `holy_guacamole_v34f` package: STEP parts, assembly, viewer, checks), which lives outside this repo. What the carrier takes from it is in `cad/rev2/README.md`. Design history and sims: `claude/v2-frame-design.md`.

### Form factor

Flat puck: Ø145 × 29 mm frame inside a Ø156 steel ring, Ø180 over the two teeth. Keeps v1's "avocado" duotone (dark green body and plates, lime rim).

### Frame

| Item | Value |
|---|---|
| Material | MJF PA11, two halves split at the ring top (z 16.9), made by an outside manufacturer |
| Plates | Top and bottom MJF PA11 0.8 mm in 0.6 mm pockets, 4 × M2.5 each (Tegris dropped: too expensive) |
| Tolerancing | v3.4f pass: every unintended face opened to ≥ 0.3 mm (MJF ±0.3), J1 middle wall 1.0 mm, USB shelves 2.6 mm deep. No access to fit coupons, so the clearances are designed in |
| Mass | 446 g CAD (limit 454); expect +1–3% from MJF density. 2.4 g trim at r44 for CoM |

### Weapon ring

AR550 3/16" (4.76 mm), Ri 73 / Ro 78, two teeth, 126 g. Six inward ears at 60° spacing (30°, 90°, … 330°) take Ti M3 × 20 button-head screws with Ø7 washers into M3 × 5.7 brass heat-sets in the upper half, 0.3 N·m. TPU ear liners (printed at home, three fits: 0.30 / 0.15 / 0.05 mm ear clearance) sit between ear and frame; use the snuggest set so the ear bears on the liner before the bolts. A full steel ring replaced v1's bolted tabs (bad bolt placement, tabs pulled out of their pockets).

### Structural results

| Check | Result |
|---|---|
| 11 kN tooth hit, static FEA | 33.6 MPa bolts-only, 30.1 MPa ring-supported, both at (47, 25, 22); FoS 1.55 on 52 MPa |
| Modal, free-free | lowest 286 Hz (battery ribs); no frame-vs-ring mode below 951 Hz; wheel-rev excitation 200 Hz at 4500 rpm |
| Skin poke, 300 N on 6 mm | first yield at 50–90 N; gussets didn't help, not adopted |
| Ring-ear joint | ear bolts bear before the liner engages unless a tighter liner is used; insert pull-out marginal under a big vertical hit |
| Assembly / service / tool access | all clear, 0 trapped cavities |

### Battery

Single GNB 3S 380 HV pack (55 × 17 × 20, 32 g) on the spin axis at x ±8.5, y −23.2…+31.6, z 7.2–27.2, leads and balance plug out of the S end, on ribs over the carrier board. On-axis, so it sees almost no centrifugal load (unlike v1's 55 mm-radius pockets).

### Motor mounting and wheels

Motors on the E/W axis, perpendicular to the teeth (prevents hockey-puck sliding). PBB D2822 1100KV, 1/8" shaft, ~70 mm leads to 2 mm bullets. Wheels Ø42 × 9 mm at r ≈ 56 mm: PA11 hub with a cast VytaFlex 40 tread (printed moulds), outboard MR128 bearing (seat reamed to 12 mm).
 
---

## 5. Operating parameters
 
Numbers for v3.4f: I ≈ 1.39e-3 kg·m² (CAD), wheel Ø42 at r 56 (chassis rpm = 0.375 × motor rpm without slip), 3S HV.

| Parameter | Value |
|---|---|
| Target chassis RPM | ~3,000 tracking / ~4,000 strike |
| No-load chassis RPM, 3S | ~4,700 at 11.4 V, ~5,400 at 13.05 V (1100 KV × V × 0.375). Real loaded figure needs the bench; 2S estimates were 2,200–2,850 |
| Tip speed at 4,000 RPM, r 90 (tooth tip) | 37.7 m/s ≈ 84 mph (ring OD r 78: 32.7 m/s) |
| G at 12 mm (U4), 4,000 RPM | ~215 g |
| G at 18 mm (U5/U6), 4,000 RPM | ~322 g |
| G at ring centreline r 75.5, 4,000 RPM | ~1,350 g |
| H3LIS331DL ceiling (392 g usable at 18 mm) | ~4,400 RPM |
| LSM6DSV320X accel ceiling (313 g at 12 mm) | ~4,800 RPM |
| LSM6DSV320X gyro ceiling (±4,000 dps) | **~667 RPM**, railed at any combat speed |
| Kinetic energy | ~69 J at 3,000 RPM, ~122 J at 4,000 RPM (½Iω²) |

The earlier "~400–600 mJ" figure was wrong by ~200×.

**Two operational modes (community-validated "pounce" strategy):**
 
| Mode | RPM | Purpose |
|---|---|---|
| Tracking | ~3,000 RPM | Stable heading, good translation authority, follow opponent |
| Strike | ~4,000–4,300 RPM | Maximum KE, accept some heading degradation, burst engagement |
 
Community consensus (jbk9925, frugez, others): translation works best at 2,000–3,500 RPM. Above 3,500 RPM heading stability degrades with naive integrators. At 5,000+ RPM translation becomes unreliable. The EKF approach should extend the reliable translation window higher than OpenMelt-style integrators, but two-mode operation remains the right combat strategy.
 
Strike mode RPM ceiling: ~4,400 RPM (outer H3LIS limit). IMU-A's accel (inner, 12 mm) stays in-spec to ~4,800 RPM, so it becomes the primary centripetal sensor during high-RPM bursts.
 
**Control loop rate requirement (community rule):**  
Minimum ~8 DSHOT updates per chassis revolution for translation. At 4,000 RPM (66.7 Hz): minimum 533 Hz. At 4,300 RPM: 573 Hz minimum. The 1 kHz loop gives ~15 updates per revolution at 4,000 RPM.
 
---

## 6. Control theory research
 
This section documents the academic literature we identified as relevant to the heading estimation and control problem. The meltybrain community has largely not engaged with this literature — there is real opportunity here.
 
### 6.1 The core problem
 
At operating RPM, the robot's gyroscope channels saturate immediately (even high-range MEMS gyros max out well below 4,000 RPM = 24,000 °/s). Heading must therefore be derived from accelerometers only. The basic approach:
 
```
centrifugal acceleration = ω² × r
→ measure a_centrifugal from IMU
→ solve for ω
→ integrate ω over time → heading θ
```
 
This works at steady state but has several failure modes: spinup/spindown (low centrifugal signal), impacts (sudden ω change), and centre-of-rotation (CoR) shifts (mixes linear acceleration into the centrifugal reading).
 
### 6.2 Gyro-Free IMU literature (GF-IMU)
 
The formal name for "estimate angular velocity from accelerometers only" is gyroscope-free IMU or GF-IMU. This has been studied for ~30 years in aerospace and robotics. The combat robotics community has not engaged with it.
 
**Key paper: arXiv:2108.09834** — "Angular Velocity Estimation Using Non-Coplanar Accelerometer Array" (Maynard & Vikas, 2021)
 
Treats the problem as a dynamical system where accelerometer readings are simultaneously process and measurement inputs. Uses an EKF that discretises and linearises the continuous-discrete system. Key result: estimation noise scales inversely with the singular values of the relative displacement matrix between sensors. This gives a principled basis for sensor placement optimisation — not just "put them at 45°" but a formal criterion for what geometry minimises noise.
 
**Key paper: arXiv:1509.06494** — Cramér-Rao bound for accelerometer arrays
 
Establishes a fundamental limit: for purely gyroscope-free IMUs there is no unbiased finite-variance estimator for small angular velocities. Practically: your heading algorithm cannot work at very low RPM, and no amount of algorithmic sophistication changes this. There is a physical floor set by sensor noise and lever arm length. For Holy Guacamole this is fine: the centrifugal signal at 4,000 RPM at 18mm radius is ~322G, well above noise. The bound matters during spinup below ~500 RPM where the signal is marginal.
 
**GFSINS literature** (gyroscope-free strapdown inertial navigation systems)
 
Multiple accelerometers fused via Kalman filter, combining an "integral algorithm" with an "extraction algorithm." These papers work out the sign ambiguity problem formally — you cannot tell the sign of ω from a single accelerometer axis, which is exactly the zero-crossing problem. Project Liftoff's 45° dual-IMU placement solves this geometrically but without the formal underpinning. The GFSINS papers provide that underpinning and suggest more optimal geometries.
 
### 6.3 Spinning spacecraft attitude estimation
 
Spinning spacecraft are the closest physical analogue: object spinning fast, gyros saturated or unavailable, need heading from other sensors. This problem has been solved rigorously in aerospace.
 
**SpinKF (NASA Goddard, NTRS 20070032655)**
 
Uses a seven-parameter angular-momentum-based state representation rather than quaternions or Euler angles. Key insight: angular momentum varies more slowly than angle for a spinning body, making it a better state variable. Between attitude measurements, angular momentum is propagated using Euler's equations of motion. The state is `[H_inertial_x, H_inertial_y, H_inertial_z, H_body_x, H_body_y, H_body_z, rotation_angle]`.
 
**Application to Holy Guacamole:** parameterise the EKF state as angular momentum rather than angle. This makes the filter more robust during spinup/spindown transitions where angle changes rapidly but angular momentum changes slowly (only when motor torque is applied). Impact events appear as sudden angular momentum changes (impulsive torque), which is easier to model than sudden angle jumps.
 
### 6.4 Disturbance rejection
 
**VQF (arXiv:2203.17024)**
 
Achieves 2.9° average RMSE vs 5.3°–16.7° for existing methods. Key architectural idea: decouple the channels so disturbance in one measurement path doesn't corrupt the other. Applied to Holy Guacamole: decouple the eRPM-based ω estimate from the accelerometer-based heading integration. An impact that corrupts the accelerometers doesn't cascade into the eRPM channel, and vice versa. Each channel provides an independent ω estimate; the filter fuses them with appropriate confidence weights.
 
**Jerk-augmented EKF for impulsive disturbances**
 
Augmenting the EKF state with jerk (dα/dt, rate of change of angular acceleration) allows the filter to model and absorb sudden ω changes from impacts. A baseline EKF constrained to constant-acceleration assumptions overshoots dramatically during impact events. The jerk-augmented filter maintains physical consistency during the spike. Practical implementation: add one state variable (jerk), add one process noise term, update the state transition matrix. Modest complexity increase for significant robustness improvement.
 
### 6.5 Centre-of-rotation estimation
 
The CoR problem is specific to meltybrain and has not been published anywhere that we found. The issue:
 
On a two-wheeled meltybrain, the instantaneous centre of rotation during a drift manoeuvre is NOT the geometric centre of the disc. It shifts based on the differential thrust ratio between the two motors. Your IMU is mounted at a fixed position relative to the geometric centre, not the instantaneous CoR.
 
The centrifugal acceleration seen by an accelerometer at position **r** from the geometric centre is:
 
```
a = ω² × |r - r_cor| × r̂_from_cor
```
 
Where `r_cor` is the CoR offset from geometric centre. If your firmware assumes `r_cor = 0` (CoR at geometric centre) when it's actually offset, you get a systematic error in ω estimation that scales with drift authority.
 
At small drift inputs the error is second-order and negligible. At aggressive drift inputs (close to full differential thrust) the CoR can shift by several millimetres and the error becomes material.
 
**The three-IMU solution:** With three accelerometers at different angular positions, you have enough equations to solve for `{ω, α, a_linear_x, a_linear_y}` simultaneously. The linear acceleration terms (`a_linear`) directly encode the CoR offset — if they are nonzero, the CoR is displaced. Solving for them gives you a real-time CoR estimate that the heading algorithm can use as a correction. This is the primary motivation for the third IMU.
 
**The radially-separated solution:** One IMU at a different radius from the others allows differencing their radial readings to cancel linear acceleration (which is the same at all radii) and isolate the centrifugal term (which scales with radius). This was considered (inner IMU at 12mm, outer at 20mm) and incorporated into the final three-IMU design.
 
### 6.6 Summary of algorithmic innovations vs OpenMelt 2
 
| Feature | OpenMelt 2 | Holy Guacamole target |
|---|---|---|
| Heading integration | Naive integrator, open loop | EKF with angular momentum state |
| IMU count | 1 | 3 (asymmetric placement, mixed radii) |
| Zero-crossing handling | Single sensor, problematic | Geometric elimination via sensor layout |
| CoR compensation | None | Solved from 3-IMU over-determined system |
| Impact recovery | None (diverges) | Jerk-augmented state, eRPM re-anchor |
| RPM source | Accelerometer only | Accelerometer + eRPM fusion |
| Spinup heading | Lost | Tangential axis integration at low RPM |
| Steering | Square wave (on/off per 180°) | Sinusoidal thrust modulation |
 
---
 
## 7. Community RPM data and operating insights
 
This section captures empirical data from the meltybrain community (Discord, builder forums) that directly affects design and firmware decisions.
 
### 7.1 RPM operating ranges by weight class
 
| Weight | Typical RPM | Max seen | Notes |
|---|---|---|---|
| 150g | 2,000–3,000 | ~4,000 | Limited by motor size |
| 1lb ant | 2,000–4,500 | 4,500 | Sweet spot 3,000–4,000. arithebiker hits 4,200+ with D2822 1100KV |
| 3lb | 1,800–3,500 | ~5,000 | More mass = harder to spin up. Project Liftoff targets ~4k |
| Beetle | 2,000–6,000 | 8,000 | jbk9925's Shadow theoretical 7k, translates at 3–5k |
 
### 7.2 Translation RPM window
 
Translation works best at 2,000–3,500 RPM. Multiple builders confirm independently:
- jbk9925: "I translate around 3k. 5k is very unstable heading"
- frugez: "translation doesn't work well above 3k rpm for some reason"
- remzakmij: above 6,000 RPM, ESC response window too short for translation pulses
- zenith_parsec: achieved translation at ~300 RPM with low-range accelerometer and good filtering
Above ~3,500 RPM naive integrators lose heading lock (visible as heading indicator becoming a full circle rather than a point). This is not a fundamental limit — it's an integrator quality limit. The EKF approach targets maintaining heading lock through the 4,000+ RPM range where naive integrators fail.
 
**Minimum viable RPM for translation:** ~300–800 RPM depending on sensor quality. At 300 RPM, 18mm radius: 1.8G centrifugal, below the noise floor for H3LIS331DL at 400G range. The tangential-axis spinup strategy (using α×r signal) handles this regime.
 
### 7.3 The pounce strategy
 
jbk9925's proven two-mode strategy: follow at ~3,000 RPM with stable heading, then punch to 4,500–5,000 RPM on engagement for maximum kinetic energy. This is now a first-class firmware requirement for Holy Guacamole:
 
- **Tracking mode (~3,000 RPM):** stable heading lock, high translation authority, pursue opponent
- **Strike mode (~4,000–4,300 RPM):** maximum KE, degraded heading acceptable, burst engagement
Implement as momentary switch on transmitter — hold to punch to strike RPM, release to return to tracking. EKF must handle the transition: when RPM setpoint changes, temporarily inflate process noise on ω state so the filter doesn't fight the intended change.
 
### 7.4 Andrew's Rules of Translational Drift
 
From remzakmij (Project Liftoff), the formal drift equation:
 
```
Drift = (Accuracy Coefficient) × (Power) × (Wheel Path / Wheel Diameter)
```
 
**Accuracy Coefficient:** how precisely you track RPM and pulse motors at the right heading. The EKF directly improves this vs naive integrator.
 
**Power:** watts delivered to ground — combination of motor power, wheel traction, and ESC response speed. AM32 > BLHeli_S here due to better low-speed torque control.
 
**Melty Ratio = Wheel Path / Wheel Diameter:**
```
Wheel path = 2π × wheel radius from centre = 2π × 56mm = 352mm per revolution
Melty ratio, v3.4f Ø42 wheel = 352 / 42 = 8.4
(old 75 mm / 20 mm concept: 471 / 20 = 23.6)
```
 
Higher ratio = more motor rotations per chassis rotation = more DSHOT update opportunities per revolution = finer translation authority. This is a real argument for smaller wheels. At 1kHz loop rate and 4,000 RPM: ~15 update points per revolution regardless of wheel diameter — the ratio affects how much ground is covered per update, not the update frequency itself. Smaller wheels = finer positional authority per update.
 
**Wheel diameter decision:** Ø42 for v3.4f, set by motor height, floor clearance and the cast tread. Smaller wheels would raise the ratio but need a lower motor.
 
### 7.5 Spinup time
 
tedster: "fast spin up is everything." Most 3lb melties reach full speed in 2–3 seconds with good traction per remzakmij's data. With D2822 1100KV on 3S and I ≈ 1.39e-3 kg·m², spinup to 3,000 RPM should be under 2 seconds (the SITL twin, with older plant numbers, reaches 3,000 RPM in ~1 s). Tracking mode RPM reached before the opponent engages, which matters for the match opening.
 
### 7.6 H3LIS331DL nonlinearity warning
 
remzakmij discovered through years of testing that apparent CoR distance changed nonlinearly with RPM due to sensor nonlinearity. He built piecewise linear calibration models to compensate. Plan for this: do not assume H3LIS331DL reads linearly across its 400G range. Characterise each sensor across the RPM range (500, 1000, 2000, 3000, 4000 RPM) during bench testing and store calibration curves as firmware constants. This is more important for IMU-B/C at 18mm (~81% of full scale at 4,000 RPM) than IMU-A at 12mm (~67%). The SITL twin shows uncorrected nonlinearity walks heading 180° in ~3 s at 2,700 RPM, so `accel_cal` is mandatory.
 
### 7.7 ESC response time limit
 
Above ~6,000 RPM, ESC response window per revolution becomes too short for reliable translation pulses (remzakmij). At 4,000–4,300 RPM we are well within the reliable window. This sets an upper bound if RPM is ever pushed higher in future revisions.
 
---
 
## 8. IMU placement — design evolution
 
### Generation 1: Handoff spec (dual 45°, same radius)
 
Two H3LIS331DL at r=20mm, 45° apart. Taken from Project Liftoff rev 7+ approach.
 
**Problem:** Both at the same radius means centrifugal signal has the same magnitude scaling at both sensors. You can separate directions (sensors point different ways) but cannot separate "ω changed" from "CoR shifted" by magnitude. Linear acceleration from CoR displacement looks identical to a centrifugal scale change.
 
### Generation 2: Radially separated (considered and rejected)
 
Two IMUs on the same radial line at different radii (e.g. 12mm and 30mm).
 
**Benefit:** Differencing the two sensors cancels linear acceleration, isolates ω²·Δr. Summing gives linear acceleration directly. Clean CoR estimation.
 
**Problem:** At 4,000 RPM, r=30mm gives ~540G — over the H3LIS331DL ±400G hard limit. Only viable at the old 1,800 RPM target. Rejected for current design.
 
### Generation 3: Three sensors, same radius, asymmetric angles (Option C baseline)
 
Three H3LIS331DL at r=20mm, angular positions 0°/90°/210°.
 
**Benefit:** 6 accelerometer axes total. Full in-plane observability — can solve for {ω, α, a_x, a_y} simultaneously. Asymmetric angular spacing (not 0°/120°/240°) eliminates 3-fold rotational symmetry which would create heading angles where two sensors give degenerate information.
 
**Why 0°/90°/210° specifically:** The 90° gap between sensors 1 and 2 makes their radial axes orthogonal — clean X/Y decomposition of linear acceleration. The 210° third sensor breaks the remaining symmetry. No heading angle has two sensors giving identical projections.
 
### Generation 4: Three sensors, mixed radii, asymmetric angles — hybrid parts (current design)
 
Three IMUs:
- IMU-A (U4): **LSM6DSV320X**, r=12mm, 0° nominal: accel ±320G + gyro ±4,000 dps
- IMU-B (U5): **H3LIS331DL**, r=18mm, 90° nominal: accel ±400G
- IMU-C (U6): **H3LIS331DL**, r=18mm, 210° nominal: accel ±400G

**As placed on rev 2:** the whole array is rotated 166° CCW to clear the XIAO (only 164–168° works): U4 (−11.64, 2.90) at 166°, U5 (−4.35, −17.47) at 256°, U6 (17.30, 4.96) at 16°. Firmware adds 166° to each nominal angle, then replaces them with measured positions.

**Why LSM6DSV320X at the inner position:** its gyro covers spin-up from rest, where the centripetal signal is absent, and acts as an impact anchor. **Correction:** ±4,000 dps is only ~667 RPM, so the gyro rails early in spin-up and is not an ω source at combat speed (the SITL twin found this; firmware drops a railed gyro). At 12 mm the accel ceiling is ~4,800 RPM. The LSM6DSV320X would saturate its accelerometer around 3,990 RPM at 18mm radius, too marginal for the outer positions, which is why H3LIS331DL ±400G stays there.
 
**SPI compatibility:** Both H3LIS331DL and LSM6DSV320X support SPI modes 0 and 3. Run shared bus at mode 0 (CPOL=0, CPHA=0) — SCK idles low, preventing deselected H3LIS331DL from misinterpreting bus traffic as I2C when CS is high.
 
**G ceiling verification:**
 
| Sensor | Part | Radius | G at 4,000 RPM | G at 4,300 RPM | Margin |
|---|---|---|---|---|---|
| IMU-A | LSM6DSV320X | 12mm | ~215G (67%) | ~248G (78%) | ✓ comfortable |
| IMU-B | H3LIS331DL | ~18mm | ~322G (81%) | ~372G (93%) | ✓ within spec |
| IMU-C | H3LIS331DL | ~18mm | ~322G (81%) | ~372G (93%) | ✓ within spec |
 
**Axis orientation (rev 2 as routed):** the chips do **not** share one convention. From the footprint rotations the radial-outward axis is **+X on U4, +Y on U5, −X on U6**; the tangential axis is the other in-plane axis on each. Firmware needs a per-chip axis/sign map (see firmware.md §9) and a bench spin to confirm signs.
 
---
 
## 9. Electronics hardware
 
### 9.1 Compute: Seeed XIAO RP2350
 
Chosen over custom RP2040 PCB from original handoff. The XIAO handles all finicky microcontroller routing (crystal, flash, USB, decoupling) — the carrier is a simple routing board.
 
| Parameter | Value |
|---|---|
| Module dimensions | 21 × 17.5 × 2.5mm |
| CPU | RP2350, dual Cortex-M33 @ 150MHz |
| FPU | Hardware floating point (Cortex-M33) — critical for EKF performance |
| Flash | 4MB W25Q32 onboard |
| Crystal | 12MHz onboard |
| Onboard LDO | RT9013-33, 500mA, max input 5.5V |
| Power input | 5V via `5V` pad — carrier supplies this from buck converter |
| Mounting | Castellated SMD pads, soldered flat to carrier + epoxy corner retention |
| PIO | Available for DSHOT and CRSF — same approach as RP2040 |
 
**Core assignment:**
 
| Core | Responsibility |
|---|---|
| Core 0 | IMU SPI DMA at 1kHz, heading EKF, RPM estimation, impact detection |
| Core 1 | CRSF decode, DSHOT output, drift control loop, LED state, telemetry |
 
**Why RP2350 over RP2040:**
- Hardware FPU — EKF matrix math runs in hardware float, roughly 5× faster than RP2040 soft-float
- This meaningfully expands how complex a filter can run at 1kHz without missing deadlines
- Cortex-M33 also has DSP extensions useful for signal processing
### 9.2 IMU array: hybrid (1× LSM6DSV320X + 2× H3LIS331DL)
 
Rev A uses a hybrid IMU array. The inner sensor (IMU-A, 12mm) is a LSM6DSV320X for its gyro channel. The outer sensors (IMU-B/C, ~18mm) are H3LIS331DL ±400G — the only practical part at that radius.
 
**IMU-A: LSM6DSV320X.** LGA-14 2.5×3mm, LCSC C26633007. Accel ±320G, gyro ±4,000 dps. The gyro rails at ~667 RPM (4,300 RPM = 25,800 °/s, 6.5× over range), so it covers spin-up from rest and impact detection only; at combat speed ω comes from the accelerometers and eRPM. At 12mm radius the accel ceiling is ~4,800 RPM.
 
**IMU-B/C: H3LIS331DL.** LGA-16L 3×3mm, LCSC C2655074 (Digi-Key 497-13903-1-ND, Mouser 511-H3LIS331DL). ±400G fixed range. Only viable option for outer positions at 18mm radius.
 
**SPI bus:** Both parts support modes 0 and 3. Run shared bus at mode 0 (CPOL=0, CPHA=0) throughout — SCK idles low so deselected H3LIS331DL sensors don't see phantom I2C clocks. Shared MISO with 33Ω isolation resistors; one CS low at a time.
 
Placement geometry and the rev-2 axis map are in Section 8.
 
### 9.3 Motors: Palm Beach Bots D2822 1100KV
 
| Parameter | Value |
|---|---|
| Source | palmbeachbots.com |
| KV | 1100 KV |
| Voltage | 2S–3S |
| Max power | 102W |
| Max current | 9.9A |
| Resistance | 0.192Ω |
| Mass | 44g |
| Diameter | 28mm |
| Shaft | 1/8" |
| Leads | ~70 mm silicone, 2 mm bullets to the ESC leads |
 
**Drive:** shaft-driven Ø42 wheel with an outboard MR128 bearing (no hub-on-bell mount). Chassis rpm ≈ 0.375 × motor rpm. No-load motor rpm on 3S: ~12,500 (11.4 V) to ~14,400 (13.05 V).
 
**Motor orientation:** E/W, perpendicular to the teeth. Prevents lateral sliding instability per Project Liftoff experience.
 
### 9.4 ESC: Repeat AM32 dual
 
**Chosen:** one Repeat AM32 dual ESC (28 × 20 mm, ~6 g, AT32F421, profile `AM32_RR_ROBOT_DUAL_ESC_F421`), standing on edge against the S bay wall with BAT/GND on the E side. Battery feed comes off the carrier's `J1` lap pads (20 AWG); signal on `J4` (JST-GH: GND, DSHOT1 white, DSHOT2 yellow, GND). BEC stays isolated.
 
Settings: DSHOT600 bidirectional with EDT (DSHOT300 only on the bench; bidirectional halves the effective command rate), active braking on (60 s spindown rule), current limit 4–5 A per channel, correct pole count.
 
**Why AM32:** community (jbk9925 and others) recommends against BLHeli_S; AM32 is actively developed, has native bidirectional DSHOT and better low-speed torque control. AM32 can't be flashed onto BLHeli_S (8-bit EFM8) hardware; for those, Bluejay is the fallback.
 
### 9.5 Radio: ExpressLRS
 
BetaFPV ELRS Lite 2.4 GHz, flat antenna (ESP8285, 11 × 10 × 3 mm), on a tray in the S pocket with the antenna outward, clear of the battery. CRSF at 420 kbaud non-inverted on the XIAO's uart0 through `J5` (JST-GH: GND, 5V, CRSF_RX, CRSF_TX). Configure over its own WiFi AP (10.0.0.1).
 
Telemetry back channel: RPM, heading error, battery voltage, current draw — log during test runs for tuning.
 
**Critical:** Configure ELRS failsafe to zero throttle on signal loss before any powered testing.
 
### 9.6 Battery: GNB 3S 380 mAh HV
 
55 × 17 × 20 mm, 32 g, 13.05 V full / 11.4 V nominal, XT30 (female on the pack, `J6` male on the board). Mounted on the spin axis over the carrier.
 
**Capacity check (open):** a 2-minute match was budgeted at ~420 mAh on 2S (spin-up ~15 A for 10 s, ~7 A steady, ~12 A impact recovery, +20% margin, +20% sag). A rough 3S estimate at ~10 A average over 3 minutes is ~500 mAh, against 380. Measure real average current on the bench soak; lower the ESC current limit or move to a larger pack if it's short.
 
UVLO: `JP1` 2-3 cuts at ~8.85 V (2.95 V/cell); `R25` 66.5k would move it to ~8.0 V. Firmware low-battery halt must sit above the hardware cutoff.
 
### 9.7 Power switch: Fingertech Mini Power Switch
 
12.7×12.7×6.35mm, 2.15g, 40A rated / 100A burst. Allen key (3/32") activation, so it cannot back out under vibration. Satisfies MRCA manual disconnect requirement. Sits in its frame socket on a short XT30 pigtail into `J7` (switch loop: VBAT_RAW out, VBUS back).
 
### 9.8 Wheels: cast urethane tread
 
Ø42 × 9 mm. PA11 hub (MJF) with a VytaFlex 40 tread cast in printed moulds (`wheel_mould` package), MR128 outboard bearing. Earlier options (EVA foam + rubber cement + latex, BaneBots T61) are superseded.
 
**Centrifugal concern:** at 4,000 RPM the tread sees ~1,000 g at r 56; spin-test before the first event and check floor clearance. Moderate grip is better than maximum grip for drift.
 
---
 
## 10. Carrier PCB specification
 
The current board is rev 2. Full detail is in `spec.md` (Rev B 2.1, which tracks `hardware/guac.kicad_sch` and `hardware/guac.kicad_pcb`). Summary:
 
- 40 × 76 × 1.6 mm, 4 layers, 2 oz outer / 1 oz inner, ENIG, centred on the spin axis, clamped under the chassis end ledges with 4 × M2. Fabbed at PCBWay (normal process: 0.18 / 0.205 mm trace/space).
- The carrier is also the power distribution board: battery on `J6` (XT30-M), switch loop on `J7` (XT30-F), ESC feed on `J1` lap pads; ~9 mΩ of board copper; outer VBUS↔VBAT_RAW kept 1 mm apart.
- AP63301 5 V buck (forced PWM), JP1 UVLO select, SMAJ15CA TVS and 100 µF polymer bulk on VBUS.
- SN74HC595 latch for the three IMU chip-selects (QD–QH NC). SK9822 chain and MCP23S17 are gone.
- JST-GH for ESC signal (`J4`), receiver (`J5`), and both TinySLEDs on one Y-splice (`J2`, Q1 AO3402 low-side).
- Flush bottom-copper debug pads only: `TP13` SWDIO, `TP14` SWDCK, `TP15` GND, `TP10` VBAT_SNS. Nothing else on the underside (0.32 mm to the bottom plate).
- Rev A had R6/R7/R8 on MOSI instead of MISO; fixed in rev 2.
 
### Pin assignment (unchanged from Rev A)
 
| XIAO pad | Signal | Notes |
|---|---|---|
| D0/A0/GPIO26 | `VBAT_SNS` | 120k / 33.2k divider |
| D1/A1/GPIO27 | `HEAD_LED` | TinySLED MOSFET gate |
| D2/A2/GPIO28 | `SEL_OE_N` | Latch output enable (active-low) |
| D3/GPIO5 | `SEL_LAT` | Latch clock |
| D4/GPIO6 | `DS1_IO` | AM32 ch1 DSHOT/EDT |
| D5/GPIO7 | `DS2_IO` | AM32 ch2 DSHOT/EDT |
| D6/TX/GPIO0 | `CRSF_TX` | To receiver |
| D7/RX/GPIO1 | `CRSF_RX` | From receiver |
| D8/SCK/GPIO2 | `SPI_SCK` | IMUs + latch, 100k pull-down |
| D9/MISO/GPIO4 | `SPI_MISO` | IMU data return |
| D10/MOSI/GPIO3 | `SPI_MOSI` | IMUs + latch |
| SWDIO/SWDCLK | debug | Bottom pads `TP13`/`TP14` |
 
### Heading LED timing reference
 
```
4,000 RPM → 1 revolution = 15ms
1° of arc  = 41.7µs
300µs pulse = 7.2° arc   ← start here
500µs pulse = 12.0° arc
```
 
### Sensors

All sensing is through the three-IMU array and AM32 EDT telemetry. No dedicated impact sensor; the piezo was dropped. (An ESP32-C3 RSSI-beacon heading source was tried in firmware and removed.)
 
---
 
## 11. Firmware architecture
 
### 11.1 Overview
 
Two-core RP2350 design. Core 0 is sensor-side (time-critical, deterministic). Core 1 is control-side (responds to core 0 state estimates).
 
```
Core 0                              Core 1
──────                              ──────
IMU SPI DMA @ 1kHz              CRSF decode (PIO or UART)
  ↓                                  ↓
Raw accel samples                RC stick inputs
  ↓                                  ↓
Saturation flags                 Drift controller
  ↓                                  ↓
Heading EKF                      DSHOT600 output (PIO, bidir)
  ↓                                  ↓
ω estimate                       eRPM / EDT telemetry read
  ↓                                  ↓
θ estimate ──────────────────→   Thrust modulator
                                 Heading LED strobe (phase-locked)
                                 TinySLED status codes (idle)
                                 CRSF telemetry tx
```
 
Inter-core communication via RP2350 hardware FIFO. Core 0 writes `{accel, gyro, timestamp}` at 1kHz. Core 1 reads and applies thrust modulation and heading strobe timing.
 
**Boot sequence requirement:** SN74HC595 latch must be initialised with all outputs blanked before any IMU SPI transaction. Firmware boot order: (1) init latch GPIOs, drive SEL_OE_N high (outputs high-Z), (2) init IMUs, (3) start DMA, (4) enable heading LED PIO.
 
### 11.2 IMU DMA and SPI bus management
 
One LSM6DSV320X + two H3LIS331DL on a shared SPI bus (shared MISO via 33Ω isolation resistors R6/R7/R8). CS lines driven by SN74HC595 latch (QA/QB/QC). Target design: DMA-driven burst reads → interrupt → core 0 processes the batch. **As built:** blocking SPI in a `busy_wait`-paced 1 kHz loop (firmware.md §8); DMA is future work.
 
**Constraint: one IMU selected at a time (Rev A and rev 2).** Because U4/U5/U6 share a single MISO net, firmware must assert exactly one CS line low during each SPI data transaction. Do not assert multiple CS lines simultaneously; all three IMUs would drive the shared MISO net simultaneously, causing bus contention. The 33Ω resistors limit contention current but do not make the data valid. Simultaneous CS assert is electrically invalid.
 
**Sequential read timing budget:**
 
| Step | Time |
|---|---|
| 40-bit X/Y burst read per IMU at 10MHz | ~4µs |
| Three ideal sequential reads | ~12µs |
| SN74HC595 latch shift+latency | ~2µs |
| Practical 3-IMU set including latch overhead | ~20–35µs |
| Angular skew at 4,000 RPM (30µs) | ~0.72° |
 
0.72° of systematic read skew is within the noise of other error sources (IMU placement accuracy ±0.1mm → ~0.3–0.5°, nonlinearity correction residuals). It is compensatable in firmware by timestamping each read and applying a fixed angular offset based on known read order and timing.
 
**Firmware requirements for efficient sequential reads:**
 
- Cache SN74HC595 latch shadow register — do not re-read before each CS toggle, maintain a local copy in firmware
- Transition CS lines with minimum overhead: one latch_set call to deassert previous sensor + assert next sensor simultaneously
- Exactly one IMU CS low during each data transaction — no exceptions
- Timestamp each read (or apply fixed compensation for known read order) if skew compensation is implemented in the EKF measurement model
**Parallel MISO (Rev B):** Routing each H3LIS331DL SDO to a separate direct RP2350 GPIO and implementing a PIO parallel SPI reader would reduce read skew to <1µs (~0.02°). Requires PCB revision — likely underside XIAO pads or pin reassignment. Not a Rev A option. Evaluate after testing whether 0.72° skew is a limiting factor.
 
**Internal ADC synchronisation caveat:** Even parallel MISO would not fully eliminate sensor-to-sensor skew, because the three H3LIS331DL chips have independent internal ADC clocks with no common external sample trigger. The INT1/INT2 data-ready pins (unused in Rev A) could be used in a future revision to synchronise internal ADC sampling — a separate improvement from parallel MISO.
 
**SK9822 gating:** no longer applies; rev 2 deleted the SK9822 chain and `U11` QD is NC.
 
### 11.3 Heading EKF
 
**State vector:**
 
```
x = [H_z, θ, ω, α, j, cor_x, cor_y]
```
 
Where:
- `H_z` — angular momentum about spin axis (scalar for planar case)
- `θ` — heading angle 0–360°
- `ω` — angular velocity (rad/s)
- `α` — angular acceleration
- `j` — jerk (dα/dt) — augmented state for impact robustness
- `cor_x, cor_y` — centre-of-rotation offset from geometric centre (mm)
**Why angular momentum as primary state:** Angular momentum is conserved between impacts (no external torque → constant H). During steady-state spinning, H changes only when motor torque is applied (known, from DSHOT command). This makes H a slowly-varying, highly predictable state variable. Angle θ changes 360° every 15ms at 4,000 RPM — much harder to propagate stably.
 
**Measurement model:** Each IMU axis provides one measurement equation. For IMU-i at position (r_i, φ_i) relative to geometric centre:
 
```
a_radial_i   = ω² × |r_i - r_cor| + noise
a_tangential_i = α × r_i + noise
```
 
With 3 sensors × 2 axes = 6 measurement equations and 7 state variables (overdetermined in the dynamical sense — the system is observable). At each timestep the EKF prediction step propagates the state forward using rotational kinematics, and the update step incorporates the 6 new accelerometer readings.
 
**eRPM and gyro fusion:** Bidirectional DSHOT600 returns electrical RPM from each ESC. Convert eRPM → mechanical RPM → ω in rad/s. Independent of accelerometers. The LSM6DSV320X gyro Z axis provides a direct ω measurement at 1kHz, also independent of accelerometers. In the EKF, eRPM is one measurement equation and gyro Z is another — giving three independent ω sources total (accelerometer array, eRPM, gyro). AM32 EDT also provides voltage, current, and temperature — log for post-match analysis.
 
**Impact detection and recovery (Rev A — gyro + eRPM + accel residual):**
1. Gyro Z sudden Δω → flag potential impact (fast path, ~1ms; only below ~667 RPM, where the gyro isn't railed)
2. Accelerometer residual spike in EKF → confirm (~1–2ms)
3. eRPM sudden change → independent check
4. On confirmed impact: inflate process noise on `{θ, ω}`, increase weight on eRPM and gyro measurements (both remain valid during impact when accelerometers saturate)
5. After ~50ms with consistent eRPM/gyro agreement: restore normal noise parameters
The gyro is particularly valuable during impact recovery — unlike the accelerometer which sees a huge centrifugal + impact signal, the gyro directly measures angular rate change. It provides a fast, clean Δω estimate at the moment of impact.
 
### 11.3b Heading LED strobe
 
The meltybrain heading indicator is a phase-locked strobe on the orange TinySLED module (J2, driven by Q1 from XIAO D1/A1). Two TinySLEDs (top and bottom) in parallel on one Y-spliced harness; at rest they also blink status codes (spec.md). Orange against the green chassis provides maximum arena contrast. **As built:** `led/head_led` runs a PIO one-shot on pio1: a 400 µs strobe once per revolution, status codes at rest, duty capped at 25% and a single pulse at about 655 ms in hardware (firmware.md §3.1).
 
**Timing:** Core 1 maintains a predicted heading angle from core 0's EKF output. At each revolution the strobe fires when the predicted heading matches the configured indicator direction (default: forward / 0° in body frame).
 
```
4,000 RPM → 1 revolution = 15ms
300µs pulse = 7.2° arc   ← start here
500µs pulse = 12.0° arc
```
 
**Implementation:** PIO state machine or hardware timer interrupt on D1/A1 (GPIO27). Must not jitter; use hardware timing, not a software loop.
 
**Safety requirements:** TinySLED modules can get hot if left continuously on. Two-layer protection required:
1. R17 (100kΩ gate pulldown) holds Q1 off at boot and firmware reset — hardware, no firmware dependency
2. PIO program must enforce maximum pulse width (e.g. 2ms hard cap) — hardware-enforced, not just a software limit. A firmware hang must not leave the LED on continuously.
### 11.4 Spinup / spindown
 
**Spinup phases:**
 
1. **Gyro coverage (0–~650 RPM):** LSM6DSV320X gyro Z integrates ω from rest and fixes the sign of ω, where the centripetal signal is absent. It rails at ±4,000 dps ≈ 667 RPM.
2. **Hand-off (~500–1,500 RPM):** the centripetal signal rises (~5G at 500 RPM at 18mm; cleaner on the inner LSM6 accel). Firmware drops the railed gyro (inflated R) and the EKF runs on the accel array; eRPM joins as a second channel once fused.
3. **Full EKF steady state (~1,500+ RPM):** accelerometer array (+ eRPM when fused). The gyro is only a rail/saturation flag at speed; impact recovery leans on eRPM and the accel residual.
4. **RPM PID (~90% of target):** switch from full throttle to RPM PID. Setpoint: tracking mode (~3,000 RPM) or strike mode (~4,000 RPM).
**Note on gyro noise integration:** Gyros accumulate drift over time (integral of noise). At 1,000 Hz ODR the LSM6DSV320X gyro noise is low, but over a 2-minute match some drift is expected. The accelerometer-derived ω and eRPM channels continuously correct gyro drift through EKF measurement updates — this is the standard MEMS fusion approach and is why having all three channels matters.
 
**Spindown (60-second rule):**
- On power removal or RC failsafe: active ESC braking engaged
- AM32 active braking drives motors as generators
- Must complete within 60 seconds per MRCA rules — verify on bench
### 11.5 Translational drift
 
**Basic principle:** By powering one motor for a portion of each revolution, a net translational force is produced. The direction of translation depends on which angular positions the thrust is applied at.
 
**Square wave (OpenMelt approach):** Motor A powered for heading 0–180°, motor B powered for 180–360°. Phase offset of the square wave relative to heading produces a net thrust vector. Simple but produces RPM ripple (one motor driving, one coasting per half-revolution).
 
**Sinusoidal modulation (target approach):** Instead of binary on/off, apply:
 
```
throttle_A(θ) = base + A × cos(θ - φ)
throttle_B(θ) = base + A × cos(θ - φ + π)
```
 
Where:
- `base` — symmetric base throttle (sets RPM via RPM PID)
- `A` — drift authority (0 = no drift, 1 = maximum drift)
- `φ` — desired drift direction (from RC stick, transformed to world frame using current heading)
Benefits over square wave:
- Smoother RPM — both motors always active, no coasting phase
- Continuous vector control rather than 1-bit direction decision
- At low `A` the heading algorithm has better conditions (less CoR shift)
- Community-confirmed: deltajuliette, anguirel both report significantly smoother translation after switching to sine waves
**Two-mode operation (pounce strategy):**
 
Transmitter momentary switch toggles between modes. EKF handles RPM transition by temporarily inflating process noise on ω when setpoint changes.
 
| Mode | base throttle | RPM | A (drift authority) | Use case |
|---|---|---|---|---|
| Tracking | ~37% | ~3,000 | 0–0.8 | Follow opponent, stable heading |
| Strike | ~52% | ~4,000 | 0–0.5 | Engagement burst, max KE |
 
In strike mode, reduce max drift authority (A ≤ 0.5) to limit CoR shift at high RPM — heading is already more stressed and large A compounds the problem.
 
**IMU-A as high-RPM fallback:** During strike mode, IMU-B/C (18mm, ~322G at 4,000 RPM) approach their ceiling. EKF reduces measurement weight on IMU-B/C as their readings approach saturation and shifts weight to IMU-A's accel (12mm, ~215G, in-spec to ~4,800 RPM) and eRPM.
 
**RC stick → drift direction:**
- Stick gives desired world-frame translation vector (X, Y)
- Convert to drift direction φ: `φ = atan2(stick_y, stick_x) - θ_current`
- Heading error maps directly to drift direction error — this is why heading quality is everything
### 11.6 Calibration procedure
 
Before first event, on bench:
 
1. **IMU axis verification:** Spin at low RPM (~500), confirm each IMU's radial axis shows centrifugal acceleration outward, tangential axis shows zero (at constant ω). If signs are wrong, fix axis orientation in firmware constants.
2. **IMU position calibration:** Measure actual IMU centroid positions (r_i, φ_i) post-assembly. Store as firmware constants. Small placement errors map directly to heading errors.
3. **H3LIS331DL nonlinearity characterisation:** Spin at 500, 1000, 2000, 3000, 4000 RPM. At each RPM record centrifugal reading vs expected (ω²r/g). Build piecewise linear correction curve per sensor. Critical for IMU-B/C at 18mm operating at ~81% of full scale, where nonlinearity is worst near saturation. remzakmij discovered this over years of tuning; do it early.
4. **CoR offset calibration:** Spin at known RPM, check if CoR estimate is zero (should be, with no drift input). If nonzero, apply trim correction.
5. **Battery imbalance trim:** Static imbalance from single-pocket battery placement detected as persistent CoR offset. Apply stored trim correction to heading algorithm.
6. **Spindown test:** Verify active braking achieves full stop within 60 seconds from 4,000 RPM.
7. **ELRS failsafe test:** Power robot, establish RC link, kill transmitter, verify motors stop within 1 second.
---
 
## 12. Mass budget (v3.4f CAD)
 
| Item | g |
|---|---:|
| Lower frame half (MJF PA11) | 66.8 |
| Upper frame half (MJF PA11) | 51.1 |
| AR550 ring | 125.8 |
| Top + bottom plates (MJF PA11 0.8) | 18.8 |
| TPU ear liners | 0.8 |
| Motors (2 × D2822) | 88.0 |
| Wheels + hubs + bearings | 16.0 |
| Battery (GNB 3S 380 HV) | 32.0 |
| Carrier PCB, populated | 12.0 |
| ESC (Repeat AM32 dual) | 6.0 |
| XT30s | 3.0 |
| Switch | 2.15 |
| USB-C extension | 1.5 |
| Receiver + LEDs | 1.3 |
| Wire | 6.5 |
| Fasteners, inserts, washers, foam | 15.3 |
| **Total** | **446** |
| Limit | 454 |
| Margin | 8 g (before MJF density spread of +1–3%, i.e. ~4–13 g) |
 
2.4 g of trim at r44 balances the CoM (x −0.23, y −0.05 before trim).
 
## 13. Event calendar
 
Buckeye Bot Bash 2 (Bellefontaine OH, Aug 29 2026) has passed and is no longer the target. No next event is set; check robotcombatevents.com and confirm meltybrain legality with each EO before entering.
 
## 14. Reference builds
 
**Project Liftoff** (NHRL, 3lb) — Most successful competitive meltybrain publicly documented. 9 iterations. Key lessons absorbed into Holy Guacamole design:
- Symmetric dual weapon tabs beat asymmetric single tab
- Dual 45° opposed accelerometers for heading (we extend this to three sensors)
- Hub motor dead axle architecture (we use this)
- Motors perpendicular to weapon axis (we use this)
- wiki.nhrl.io/wiki/index.php/Project_LiftOff
**DeepMelt** — Autonomous variant of Liftoff. IR-based opponent detection. Predecessor concept for Holy Guacamole II.
- wiki.nhrl.io/wiki/index.php/DeepMelt
**Open Melt 2** — Open source Arduino meltybrain firmware. Single accelerometer heading algorithm. Starting reference for firmware development — we extend and replace the core heading algorithm substantially.
- github.com/nothinglabs/openmelt2
**Pac-Attac** — 1lb meltybrain. Dual accelerometer approach (16G + 200G range switching by RPM). Different solution to the range problem than we use.
- robowarner.com/portfolio/pac-attac-1lb-meltybrain/
---
 
## 15. Open questions
 
### Before the PCBWay order
 
1. **`C21` part number.** Still TBD in the PCBWay BOM (100 µF / 25 V polymer tantalum, 7343-43, ≤ 4.3 mm).
2. **3S UVLO cutoff.** Keep `R25` 75k (~8.85 V) or change to 66.5k (~8.0 V).
3. **TinySLED at 13.05 V.** Confirm the 2–3S module tolerates it, or use the 3–6S version.
 
### Bring-up and bench
 
4. **First power-up** on a current-limited supply; check 5V/3V3, then IMU WHO_AM_I over Mode 0. LSM6: set `IF_CFG.I2C_I3C_disable`, ±320G + ±4,000 dps at 1 kHz.
5. **IMU axis/sign map and positions.** Implement the per-chip map (+X U4, +Y U5, −X U6 radial) and measure positions (§11.6 steps 1–2).
6. **Bench soak.** 3 minutes at the ESC current limit; copper/connector temperature, real average current vs the 380 mAh pack.
7. **Real chassis RPM on 3S.** Validate against the ~4,700 RPM no-load estimate; update firmware plant parameters (firmware.md §9).
8. **H3LIS331DL nonlinearity characterisation.** Multi-RPM curves per sensor (§11.6 step 3) before heading tuning.
9. **Spindown.** Active braking to a stop within 60 s from strike RPM.
10. **Heading LED.** The hardware-capped PIO one-shot is in firmware; tune pulse width and phase with a scope, and check TinySLED temperature at the status-code duty.
11. **Power integrity.** Scope VBUS, 5V, 3V3 during spin-up, regen braking, and strobes.
12. **Two-mode RPM validation.** Stable heading at tracking, acceptable at strike; tune EKF noise inflation on mode changes.
 
### Mechanical (no coupons available)
 
13. **First MJF parts.** Check the fit against the v3.4f audit on arrival (ring slot, bearing seats, battery ribs, plate pockets).
14. **Ear liner fit.** Pick the snuggest of the three TPU fits that slides on.
 
### Future
 
15. **Opponent sensing (Holy Guacamole II).** A spinning IR lidar. Any new sensor needs a connector on a later board; rev 2 has only the bottom debug pads.
16. **INA180 / shunt.** If EDT current telemetry latency proves insufficient.
17. **ESC BEC characterisation.** Measure under load before ever tying it to the carrier 5 V.
18. **ESC on the carrier.** Dual AM32 on the 4-layer board; saves ~6 g, large project.
19. **EKF tuning constants and 7-state filter.** Log bench data, replay in the SITL twin, tune offline; then CoR / jerk / eRPM fusion.
20. **Impact detection tuning.** Strike a fixed target at known speeds and set thresholds from gyro/eRPM/accel data.
---
 
*Last updated: v2.0 (2026-11-10). Refreshed to chassis v3.4f and the rev 2 carrier: MJF PA11 frame, AR550 ring, 3S HV 380, AM32 dual, Ø42 cast wheels, 40×76 4-layer PDB carrier for PCBWay; gyro-rail correction (~667 RPM); KE recomputed; rev 2 IMU rotation and axis map; mass budget from CAD. v1.4: SN74HC595 replaced MCP23S17, piezo removed.*
