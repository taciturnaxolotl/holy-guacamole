# Holy Guacamole — Full Project Braindump
 
**Robot:** Holy Guacamole — 1lb meltybrain antweight, MRCA full-combat ruleset  
**Document type:** Running knowledge dump — research, design decisions, hardware, firmware architecture  
**Target event:** Buckeye Bot Bash 2, Bellefontaine OH, Aug 29 2026  
**Status:** Pre-build, PCB spec complete, chassis design in progress
 
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
 
A well-tuned meltybrain is simultaneously a full-body spinner (kinetic energy in the rotating mass) and a controlled mobile robot. The chassis IS the weapon. At 4,000 RPM and 75mm radius the tip speed is approximately 70 mph. Combined with metal weapon tabs, this is a meaningful combat machine.
 
The autonomous sensing extension (Holy Guacamole II) exploits the spinning geometry in a novel way: IR sensors spinning at 4,000 RPM scan the arena 67 times per second, building a polar reflectance map that can locate opponents without any external tracking infrastructure. This is impossible on a stationary robot and is one of the genuinely novel things this platform enables.
 
---
 
## 2. Robot concept and goals
 
**Name:** Holy Guacamole  
"Holy Guacamole" — chaotic energy, memorable pit presence.
"II" implies a lineage. Holy Guacamole II adds IR spinning lidar for autonomous opponent tracking.
 
**Design philosophy:**
- Holy Guacamole is a proof-of-platform. Manual RC control, validate the heading algorithm, prove the mechanical design survives combat.
- Holy Guacamole II upgrades the IMU fusion algorithm and adds spinning IR opponent detection.
- Keep the build achievable before the August 2026 deadline. Don't over-engineer Rev 1.
**Combat strategy:**
- Spin up to 4,000 RPM before engaging
- Translate toward opponent using drift control
- Weapon tabs at N/S, motors at E/W — weapon axis is perpendicular to drive axis
- Full invertibility — symmetric top/bottom design means being flipped is not a loss condition
---
 
## 3. Ruleset constraints (MRCA full antweight)
 
| Rule | Detail |
|---|---|
| Weight limit | 1.00 lb / 454g for wheeled robots |
| Materials | No restrictions — metal, UHMW, Delrin, carbon fiber all permitted |
| Active weapon | Meltybrain legality must be confirmed with each event organizer. MRCA ruleset lists "rolling (wheels, tracks, or the whole robot)" as permitted mobility and does not explicitly ban translational drift. **Confirm with Buckeye Bot Bash EO before committing to build.** |
| Spindown | Full stop within 60 seconds of power removal, self-contained braking. Active ESC braking satisfies this. |
| Failsafe | Radio must failsafe all motion (drive + weapon) on signal loss |
| Battery | LiPo permitted. Must be fully enclosed. Uncontained battery = automatic KO. |
| Arena | MDF floor, ¼" polycarbonate walls, ~6×6ft nominal |
| Match duration | 2 minutes |
| Pinning limit | 5 seconds max |
 
**Key note:** This is full-combat antweight, NOT plastic ant. Metal weapon tabs, UHMW chassis reinforcement, and carbon fiber are all permitted. Design accordingly.
 
---
 
## 4. Chassis design
 
### Form factor
 
Flat disc, 150mm OD, ~22mm max height at centre, flat puck profile. NOT lenticular/tapered — flat puck maximises wall count for structural strength and is trivially printable on a standard FDM printer.
 
### Weapon geometry
 
Two symmetric wedge tabs at 180° apart (N/S), protruding radially outward beyond the main disc radius in the horizontal plane only. Each tab has:
- Hard leading face approximately 90° to tangent — maximum impact energy transfer
- Smooth trailing taper back to disc radius over ~40° of arc — reduces drag and deflection
- Symmetric top/bottom for full invertibility
Metal tab inserts (Ti-6Al-4V titanium preferred, steel acceptable) bolted through from chassis body. Full-combat ruleset means no reason to use printed tabs.
 
### Print strategy
 
| Parameter | Value |
|---|---|
| Printer | Bambu A1 Mini (180×180mm bed, 0.4mm nozzle → 0.42mm extrusion width) |
| Material | Overture Super PLA+ — ductile failure mode, bends before breaking |
| Avoid | Duramic PLA+ — more brittle, worse for impact |
| Orientation | Flat on bed (disc face down) — layer lines horizontal, impacts load in tension/compression not delamination |
| Wall strategy | Maximum perimeters in multiples of 0.42mm. Wall count matters more than infill percentage. |
| Infill | ~80% gyroid |
| Seam placement | Away from battery pocket locations |
| Supports | None needed for flat disc geometry |
 
### Battery pockets
 
Two rectangular pockets at 180° (N/S), at ~55mm radius from centre. Batteries oriented with flat face tangential to rotation — centrifugal force compresses cell layers together, not apart. Pockets fully enclosed, batteries epoxy-potted in place. Must not eject under any loading condition.
 
### Motor mounting
 
Motors mount E/W (perpendicular to weapon tab axis N/S). This is a deliberate choice from Project Liftoff experience — motors at E/W prevent the robot from sliding sideways like a hockey puck when the weapon tabs face N/S. Drive axis perpendicular to weapon axis.
 
Hub motor architecture: the rotating motor bell/can is the wheel hub. Custom wheel hub attaches directly to the spinning can via 3× M2 holes on a 12mm bolt circle. Stator backplate bolts to chassis (fixed). This eliminates a dedicated axle and keeps mass close to the wheel.
 
One outboard R2ZZ bearing (1/8" ID × 3/8" OD) at each motor shaft tip, press-fit into a printed chassis arm extending to 75mm radius. Eliminates shaft flex from the ~45mm wheel overhang.
 
---
 
## 5. Operating parameters
 
| Parameter | Value |
|---|---|
| Target chassis RPM | 4,000 RPM (tunable 3,500–4,500) |
| Motor throttle at 4,000 RPM | ~65% — healthy thermal margin |
| Tip speed at 4,000 RPM, 75mm radius | ~70 mph |
| G at 12mm radius (inner IMU), 4,000 RPM | ~216G |
| G at 20mm radius (outer IMUs), 4,000 RPM | ~360G |
| G at 55mm radius (battery), 4,000 RPM | ~990G |
| G at 75mm radius (chassis edge), 4,000 RPM | ~1,350G |
| H3LIS331DL limit | ±400G hard ceiling |
| RPM ceiling (outer IMU at 20mm) | ~4,300 RPM before hitting 400G |
| Kinetic energy | ~400–600 mJ depending on final mass distribution |
 
**Why 4,000 RPM (revised upward from 1,800 RPM):**
- Motors run more efficiently at 65% throttle vs 30%
- Full-combat ruleset permits metal tabs — more damage at higher tip speed
- H3LIS331DL at 20mm radius has margin up to ~4,300 RPM before hitting G ceiling
- eRPM telemetry provides secondary RPM anchor independent of IMU
- Community data point: arithebiker runs D2822 1100KV at 4,200+ RPM successfully — validates motor choice empirically
**Two operational modes (community-validated "pounce" strategy):**
 
| Mode | RPM | Purpose |
|---|---|---|
| Tracking | ~3,000 RPM | Stable heading, good translation authority, follow opponent |
| Strike | ~4,000–4,300 RPM | Maximum KE, accept some heading degradation, burst engagement |
 
Community consensus (jbk9925, frugez, others): translation works best at 2,000–3,500 RPM. Above 3,500 RPM heading stability degrades with naive integrators. At 5,000+ RPM translation becomes unreliable. The EKF approach should extend the reliable translation window higher than OpenMelt-style integrators, but two-mode operation remains the right combat strategy.
 
Strike mode RPM ceiling: 4,300 RPM (outer IMU G limit). IMU-A (inner, 12mm) stays in-spec up to ~5,500 RPM — it becomes the primary sensor during high-RPM bursts when IMU-B/C approach their limit.
 
**Control loop rate requirement (community rule):**  
Minimum ~8 DSHOT updates per chassis revolution for translation. At 4,000 RPM (66.7 Hz): minimum 533Hz. At 4,300 RPM: 573Hz minimum. Our 1kHz loop rate on core 0 is comfortable at both operating points with ~15 update opportunities per revolution at 4,000 RPM.
 
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
 
Establishes a fundamental limit: for purely gyroscope-free IMUs there is no unbiased finite-variance estimator for small angular velocities. Practically: your heading algorithm cannot work at very low RPM, and no amount of algorithmic sophistication changes this. There is a physical floor set by sensor noise and lever arm length. For Holy Guacamole this is fine — the centrifugal signal at 4,000 RPM at 20mm radius is ~360G, well above noise. The bound matters during spinup below ~500 RPM where the signal is marginal.
 
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
 
**Minimum viable RPM for translation:** ~300–800 RPM depending on sensor quality. At 300 RPM, 20mm radius: 2.6G centrifugal — below noise floor for H3LIS331DL at 400G range. The tangential-axis spinup strategy (using α×r signal) handles this regime.
 
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
Wheel path = 2π × chassis_radius = 2π × 75mm = 471mm per revolution
Melty ratio at 20mm wheel = 471 / 20 = 23.6
Melty ratio at 25mm wheel = 471 / 25 = 18.8
```
 
Higher ratio = more motor rotations per chassis rotation = more DSHOT update opportunities per revolution = finer translation authority. This is a real argument for smaller wheels. At 1kHz loop rate and 4,000 RPM: ~15 update points per revolution regardless of wheel diameter — the ratio affects how much ground is covered per update, not the update frequency itself. Smaller wheels = finer positional authority per update.
 
**Wheel diameter decision:** err toward smaller once motors are in hand and clearance is confirmed.
 
### 7.5 Spinup time
 
tedster: "fast spin up is everything." Most 3lb melties reach full speed in 2–3 seconds with good traction per remzakmij's data. With D2822 1100KV on 2S and estimated inertia, spinup to 3,000 RPM should be under 2 seconds. Tracking mode RPM reached before opponent engages — important for match opening.
 
### 7.6 H3LIS331DL nonlinearity warning
 
remzakmij discovered through years of testing that apparent CoR distance changed nonlinearly with RPM due to sensor nonlinearity. He built piecewise linear calibration models to compensate. Plan for this: do not assume H3LIS331DL reads linearly across its 400G range. Characterise each sensor across the RPM range (500, 1000, 2000, 3000, 4000 RPM) during bench testing and store calibration curves as firmware constants. This is more important for IMU-B/C at 20mm (operating at 90% of full scale at 4,000 RPM) than IMU-A at 12mm (54% of full scale).
 
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
- IMU-A (U4): **LSM6DSV320X**, r=12mm, 0° — accel ±320G + gyro ±4,000 dps
- IMU-B (U5): **H3LIS331DL**, r=~18mm, 90° — accel ±400G
- IMU-C (U6): **H3LIS331DL**, r=~18mm, 210° — accel ±400G
**Why LSM6DSV320X at the inner position:** The gyro channel (±4,000 dps = ~38,200 RPM equivalent) does not saturate at any planned operating speed. At 12mm radius the accel ceiling is ~5,500 RPM — well clear. The gyro provides direct ω integration from rest, replacing the spinup dead zone feedforward model with real data, and adds a third independent ω source to the EKF alongside the accelerometer array and eRPM. The LSM6DSV320X would saturate its accelerometer around 3,990 RPM at 18mm radius — too marginal for the outer positions, which is why H3LIS331DL ±400G stays there.
 
**SPI compatibility:** Both H3LIS331DL and LSM6DSV320X support SPI modes 0 and 3. Run shared bus at mode 0 (CPOL=0, CPHA=0) — SCK idles low, preventing deselected H3LIS331DL from misinterpreting bus traffic as I2C when CS is high.
 
**G ceiling verification:**
 
| Sensor | Part | Radius | G at 4,000 RPM | G at 4,300 RPM | Margin |
|---|---|---|---|---|---|
| IMU-A | LSM6DSV320X | 12mm | ~215G (67%) | ~248G (78%) | ✓ comfortable |
| IMU-B | H3LIS331DL | ~18mm | ~322G (81%) | ~372G (93%) | ✓ within spec |
| IMU-C | H3LIS331DL | ~18mm | ~322G (81%) | ~372G (93%) | ✓ within spec |
 
**Axis orientation convention:** Each chip mounted with X axis pointing radially outward, Y axis pointing tangentially. This makes the measurement model clean: radial axis gives centrifugal + CoR linear, tangential axis gives αr + tangential linear. Verify against H3LIS331DL datasheet before PCB layout.
 
---
 
## 9. Electronics hardware
 
### 8.1 Compute: Seeed XIAO RP2350
 
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
### 8.2 IMU array: hybrid — 1× LSM6DSV320X + 2× H3LIS331DL
 
Rev A uses a hybrid IMU array. The inner sensor (IMU-A, 12mm) is a LSM6DSV320X for its gyro channel. The outer sensors (IMU-B/C, ~18mm) are H3LIS331DL ±400G — the only practical part at that radius.
 
**IMU-A: LSM6DSV320X** — LGA-14 2.5×3mm, LCSC C26633007, 198 units in stock. Accel ±320G, gyro ±4,000 dps. Gyro does not saturate at any planned operating speed (4,300 RPM = 25,800 °/s, well under the 38,200 °/s ceiling). At 12mm radius accel ceiling is ~5,500 RPM. Adds direct ω during spinup and a third independent EKF ω source.
 
**IMU-B/C: H3LIS331DL** — LGA-16L 3×3mm, LCSC C2655074, 22 units in stock — **order extras immediately.** ±400G fixed range. Only viable option for outer positions at ~18mm radius.
 
**SPI bus:** Both parts support modes 0 and 3. Run shared bus at mode 0 (CPOL=0, CPHA=0) throughout — SCK idles low so deselected H3LIS331DL sensors don't see phantom I2C clocks. Shared MISO with 33Ω isolation resistors; one CS low at a time.
 
Placement geometry documented in Section 7.
 
### 8.3 Motors: Palm Beach Bots D2822 1100KV
 
| Parameter | Value |
|---|---|
| Source | palmbeachbots.com, $14.99 each |
| KV | 1100 KV |
| Voltage | 2S–3S (7.4V–11.1V) |
| Max power | 102W |
| Max current | 9.9A |
| Resistance | 0.192Ω |
| Mass | 44g |
| Diameter | 28mm |
| Connectors | 3.5mm female bullet connectors |
 
**Hub motor architecture:** Rotating bell/can has 3× M2 holes on 12mm bolt circle for direct wheel hub attachment. Stator backplate fixed to chassis. No separate axle.
 
**No-load RPM:** 1100 KV × 7.4V = 8,140 RPM. At 65% throttle: ~4,000 RPM chassis spin.
 
**Motor orientation:** E/W (perpendicular to N/S weapon tabs). Prevents lateral sliding instability per Project Liftoff experience.
 
**Outboard bearing:** One R2ZZ (1/8" ID × 3/8" OD) per motor at shaft tip. Press-fit into chassis arm at 75mm radius. Eliminates shaft flex from ~45mm wheel overhang.
 
### 8.4 ESCs
 
**Community finding:** Multiple community members (jbk9925 and others) explicitly recommend against BLHeli_S. AM32 is strongly preferred — actively developed, native bidirectional DSHOT, better low-speed torque control. Project Liftoff uses AM32.
 
**The core constraint:** BLHeli_S runs on 8-bit EFM8 (SiLabs) MCUs. AM32 targets ARM-based 32-bit MCUs (STM32F051, STM32G071, AT32F421). These are incompatible silicon — you cannot flash AM32 onto a BLHeli_S ESC. Attempting this bricks the ESC.
 
**Preferred option: Repeat Micro AM32 ESC (×2)**
 
| Parameter | Value |
|---|---|
| Source | palmbeachbots.com or repeat-robotics.com, $19.99 each |
| Firmware | AM32, pre-flashed and combat-tuned for brushless drive |
| Dimensions | 12×18mm — smallest AM32 ESC on market |
| Mass | ~3-4g estimated (no connectors) |
| Current | Rated for 1lb/3lb drive |
| BEC | None |
| Connectors | Solder pads only — solder motor leads direct |
| Bidirectional DSHOT | Native, no configuration needed |
 
Pre-programmed for smooth bidirectional movement, should work with D2822 with minimal tuning. Check stock before ordering — goes in and out.
 
**Fallback option: Repeat AM32 35A single ESC (×2)**
 
| Parameter | Value |
|---|---|
| Source | palmbeachbots.com, $24.99 each |
| Dimensions | 25×13×5mm |
| Mass | ~5g |
| Current | 35A continuous — 3.5× motor max, runs very cool |
 
Larger and heavier than Micro but more current headroom and more consistently in stock.
 
**If using existing PBB 20A BLHeli_S ESCs: flash Bluejay**
 
Bluejay is open-source firmware for EFM8-based BLHeli_S ESCs that unlocks bidirectional DSHOT and RPM filtering. Drop-in replacement, no hardware change. Flash via esc-configurator.com in Chrome. Fully functional for Rev 1 if AM32 ESCs are unavailable.
 
Bluejay configuration (same as BLHeli_S was, now via ESC Configurator web tool):
- Bidirectional DSHOT: enabled
- Protocol: DSHOT300
- Motor timing: Medium-High
- Active braking: Enabled (60-second spindown rule)
- Startup beep: Disabled
- PWM frequency: 48kHz (Bluejay supports higher than stock BLHeli_S)
### 8.5 Radio: ExpressLRS
 
CRSF protocol, single UART to XIAO RP2350. Lower latency than FlySky iBUS — important for drift control loop timing.
 
Any ELRS receiver under ~3g. EP1, EP2, TCXO variants all work. Mount off-PCB on chassis wall for antenna clearance; fly-lead to carrier PCB.
 
Telemetry back channel: RPM, heading error, battery voltage, current draw — log during test runs for tuning.
 
**Critical:** Configure ELRS failsafe to zero throttle on signal loss before any powered testing.
 
### 8.6 Battery: 2S LiPo 300–450mAh 75C+
 
**Capacity requirement calculation (2-minute match):**
 
| Phase | Duration | Current | mAh |
|---|---|---|---|
| Spinup | 10s | ~15A avg | ~42 |
| Steady state | 90s | ~7A | ~175 |
| Impact recovery | 20s | ~12A | ~67 |
| Logic | 120s | 0.3A | ~10 |
| Subtotal | | | ~294 |
| +20% safety | | | +59 |
| +20% voltage sag | | | +59 |
| **Required** | | | **~420mAh** |
 
**C rating:** Peak ~20A / 0.35Ah = 57C minimum. Choose 75C+ rated cells.
 
**Recommended cells:**
 
| Cell | Capacity | C rating | Mass | Notes |
|---|---|---|---|---|
| GNB 2S 300mAh 80C | 300mAh | 80C | ~20g | Compact, tight on capacity |
| Dogcom 2S 350mAh 100C | 350mAh | 100C | ~22-25g | Sweet spot |
| Tattu 2S 450mAh 75C | 450mAh | 75C | ~29g | Most margin, physically large |
 
Physical limits: max 60×30×15mm. Epoxy-potted in chassis pocket. XT30 connector (NOT JST — vibration loosens crimp contacts). At 55mm radius: ~990G centrifugal. Cell layers compressed together tangentially — safe orientation.
 
### 8.7 Power switch: Fingertech Mini Power Switch
 
12.7×12.7×6.35mm, 2.15g, 40A rated / 100A burst. Allen key (3/32") activation — cannot back out under vibration. Satisfies MRCA manual disconnect requirement. Place accessible from outside chassis via recessed pocket.
 
### 8.8 Wheels: EVA foam + rubber cement + latex
 
Target diameter: determined by motor mount height. Wheel radius = mount height above floor + 3-4mm clearance. Likely 20–25mm. Finalise once motor is in hand.
 
**Grip coating procedure:**
1. Clean foam with isopropyl alcohol, dry completely
2. Two coats Elmer's rubber cement, dry between coats
3. Two coats liquid latex, dry overnight each
Rubber cement is essential primer — without it latex peels adhesively. With it, latex fails cohesively (takes foam with it, much stronger bond).
 
**Centrifugal concern:** At 4,000 RPM foam deforms outward, increasing effective wheel radius and changing floor clearance. Use high shore hardness EVA foam. Do a spin test before first event and check clearance hasn't changed.
 
**Meltybrain note:** Wheel grip is less critical than on a standard drive robot — the chassis is spinning and translating via differential thrust modulation. Excessive grip can actually interfere with the translational drift mechanism. Moderate grip is better than maximum grip.
 
---
 
## 10. Carrier PCB specification
 
Full detail in `spec.md` (current: v1.3c, matches `circuit.py` Rev A schematic). Summary here.
 
### Role
 
Routing board for the XIAO RP2350 module. The XIAO provides compute, flash, crystal, USB, and 3.3V regulation. The carrier provides:
 
- 7.4V → 5V buck conversion (AP63205 fixed-5V, TSOT-23-6)
- SPI-loaded SN74HC595 latch for IMU chip-selects and SK9822 output-enable gating
- IMU SPI routing to one LSM6DSV320X + two H3LIS331DL
- Two bidirectional DSHOT/EDT signal lines to Repeat AM32 Dual ESC (one board, two channels)
- CRSF UART to ELRS receiver
- Battery voltage sense (resistor divider → ADC)
- Dedicated meltybrain heading LED driver: external orange TinySLED module via single AO3402 MOSFET low-side switch (Q1) from XIAO D1/A1
- SK9822 status LED (2×2mm, SPI via AHCT level-shift buffers, gated by SN74HC595 QD)
- Test points on all signals
### Key architectural decisions (Rev A)
 
**AP63205 fixed-5V buck (replaces AP63203):** Fixed-output variant — no feedback resistors, simpler layout, one fewer tuning error mode. Same SOT package family, same inductor.
 
**SN74HC595 SPI-loaded latch:** XIAO edge pads are pin-limited. The latch provides IMU CS lines (QA/QB/QC) and SK9822 `LED_OE_N` gate (QD), consuming only shared SPI MOSI/SCK plus two direct GPIO controls (`SEL_OE_N` and `SEL_LAT`). Critical firmware requirement: `LED_OE_N` must be deasserted during all IMU SPI transactions. Latch update protocol: blank outputs (`SEL_OE_N` high) → shift byte on SPI → pulse `SEL_LAT` → enable outputs (`SEL_OE_N` low) for selected target only.
 
**Dedicated heading LED driver (simplified in v1.3):** The meltybrain heading strobe uses a single AO3402 MOSFET (Q1) low-side switch driven from XIAO D1/A1 (edge pad — no underside pad dependency). External orange TinySLED module (Tiny's LEDs, 2-3S rated) powered from switched VBUS (7.4V nominal). Module has onboard current limiting — no series resistor on carrier. Orange chosen for maximum contrast against green chassis filament. Heading LED current loop runs from VBUS directly — route like a battery wire, not a logic trace.
 
Previous v1.2 design used three MOSFETs (Q1/Q2/Q3) and a common-anode RGB LED on D1/D11/D12. Simplified to single MOSFET + fixed-colour orange module after confirming D11/D12 are underside pads not accessible without assembly complexity.
 
**D11/D12 confirmed NC:** XIAO RP2350 underside pads — unused in Rev A. All runtime IO on edge/castellated pads D0–D10 only.
 
**DSHOT600 (required):** At 4,300 RPM strike mode, bidirectional DSHOT halves effective command rate. DSHOT300 → 500 effective Hz (marginal). DSHOT600 → 1,000 effective Hz (required). Use DSHOT600.
 
**INA180 / shunt removed (Rev A):** AM32 EDT provides per-channel current telemetry over the DSHOT wire. INA180 deferred to Rev B if EDT latency proves insufficient.
 
**ESC BEC deliberately isolated:** BEC current rating unconfirmed. Rev A keeps AP63205 buck. Rev B may eliminate it if BEC is confirmed ≥500mA and clean under load. Add solder jumper pads in Rev A to enable zero-rework Rev B change.
 
**Board dimensions: 40×50mm rectangular:** Provides ample clearance for IMU radii (inner 12mm, outer 18mm) with room for solder mask, routing, and connector pads. Board center at (20, 25) is the rotation reference point.
 
### Physical
 
- Shape: 40×50mm rectangular with rounded corners
- Thickness: 1.0mm preferred
- XIAO: castellated SMD pads, soldered flat, epoxy corner fillet
- Fabrication: JLCPCB, ENIG, 2-layer, 0.1mm min trace/space
- Assembly: LGA-16L IMUs require paste + reflow; hand-soldering not feasible
### Pin assignment (Rev A)
 
| XIAO pad | Signal | Notes |
|---|---|---|
| D0/A0/GPIO40 | `VBAT_SNS` | Battery voltage divider ADC |
| D1/A1/GPIO41 | `HEAD_LED` | Orange TinySLED MOSFET gate drive |
| D2/A2/GPIO42 | `SEL_OE_N` | SN74HC595 output enable (active-low) |
| D3/A3/GPIO43 | `SEL_LAT` | SN74HC595 latch clock |
| D4/SDA/GPIO6 | `DS1_IO` | AM32 Ch1 DSHOT/EDT bidir |
| D5/SCL/GPIO7 | `DS2_IO` | AM32 Ch2 DSHOT/EDT bidir |
| D6/TX/GPIO0 | `CRSF_TX` | UART TX to ELRS |
| D7/RX/GPIO1 | `CRSF_RX` | UART RX from ELRS |
| D8/SCK/GPIO2 | `SPI_SCK` | IMUs + SN74HC595 + SK9822 buffers |
| D9/MISO/GPIO4 | `SPI_MISO` | IMU data return only |
| D10/MOSI/GPIO3 | `SPI_MOSI` | IMUs + SN74HC595 + SK9822 buffers |
| D11 | NC | Underside pad, unused in Rev A |
| D12 | NC | Underside pad, unused in Rev A |
| SWDIO/SWDCLK | debug | Test pads |
 
⚠ **D11/D12 confirmed NC:** XIAO RP2350 underside pads — unused in Rev A. All runtime IO on edge/castellated pads D0–D10 only.
 
### Heading LED timing reference
 
```
4,000 RPM → 1 revolution = 15ms
1° of arc  = 41.7µs
300µs pulse = 7.2° arc   ← start here
500µs pulse = 12.0° arc
100µs pulse = 2.4° arc   ← minimum useful width
```
 
Phase-lock the orange strobe to the EKF heading estimate. Start at 300µs and tune for arena visibility.
 
### Sensors

All sensing is through the three-IMU array and AM32 EDT telemetry. No dedicated impact sensor in Rev A.
 
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
Piezo event monitor              Drift controller
  ↓                                  ↓
Heading EKF                      DSHOT600 output (PIO, bidir)
  ↓                                  ↓
ω estimate                       eRPM / EDT telemetry read
  ↓                                  ↓
θ estimate ──────────────────→   Thrust modulator
                                 Heading LED strobe (phase-locked)
                                 SK9822 status LED (gated)
                                 CRSF telemetry tx
```
 
Inter-core communication via RP2350 hardware FIFO. Core 0 writes `{accel, gyro, timestamp}` at 1kHz. Core 1 reads and applies thrust modulation and heading strobe timing.
 
**Boot sequence requirement:** SN74HC595 latch must be initialised with all outputs blanked before any IMU SPI transaction. Firmware boot order: (1) init latch GPIOs, drive SEL_OE_N high (outputs high-Z), (2) init IMUs, (3) start DMA, (4) enable heading LED PIO.
 
### 11.2 IMU DMA and SPI bus management
 
One LSM6DSV320X + two H3LIS331DL on a shared SPI bus (shared MISO via 33Ω isolation resistors R6/R7/R8). CS lines driven by SN74HC595 latch (QA/QB/QC). DMA-driven burst reads — no CPU involvement in data capture. At 1kHz ODR with 3 sensors: 6 axis readings per millisecond. DMA completes → interrupt → core 0 wakes, processes batch, sleeps.
 
**Rev A constraint — one IMU selected at a time:** Because U4/U5/U6 share a single MISO net, firmware must assert exactly one CS line low during each SPI data transaction. Do not assert multiple CS lines simultaneously — all three IMUs would drive the shared MISO net simultaneously, causing bus contention. The 33Ω resistors limit contention current but do not make the data valid. Simultaneous CS assert is electrically invalid on Rev A hardware.
 
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
 
**SK9822 gating:** The SK9822 status LED shares the IMU SPI SCK/MOSI nets but is isolated by AHCT level-shift buffers with output-enable `LED_OE_N` controlled by SN74HC595 QD. Firmware must keep `LED_OE_N` deasserted during all IMU and latch SPI transactions. SK9822 update procedure: complete current IMU DMA cycle → latch LED_OE_N low → clock SK9822 24-bit frame at 1MHz (~24µs) → latch LED_OE_N high → resume IMU DMA.
 
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
1. Gyro Z sudden Δω → flag potential impact (fast path, ~1ms)
2. Accelerometer residual spike in EKF → confirm (~1–2ms)
3. eRPM sudden change → independent check
4. On confirmed impact: inflate process noise on `{θ, ω}`, increase weight on eRPM and gyro measurements (both remain valid during impact when accelerometers saturate)
5. After ~50ms with consistent eRPM/gyro agreement: restore normal noise parameters
The gyro is particularly valuable during impact recovery — unlike the accelerometer which sees a huge centrifugal + impact signal, the gyro directly measures angular rate change. It provides a fast, clean Δω estimate at the moment of impact.
 
### 11.3b Heading LED strobe
 
The meltybrain heading indicator is a phase-locked strobe on the orange TinySLED module (J2, driven by Q1 from XIAO D1/A1). Separate from the SK9822 status LED. Orange against green chassis filament provides maximum arena contrast.
 
**Timing:** Core 1 maintains a predicted heading angle from core 0's EKF output. At each revolution the strobe fires when the predicted heading matches the configured indicator direction (default: forward / 0° in body frame).
 
```
4,000 RPM → 1 revolution = 15ms
300µs pulse = 7.2° arc   ← start here
500µs pulse = 12.0° arc
```
 
**Implementation:** PIO state machine or hardware timer interrupt on D1/A1 (GPIO41). Must not jitter — use hardware timer capture, not a software loop.
 
**Safety requirements:** TinySLED modules can get hot if left continuously on. Two-layer protection required:
1. R17 (100kΩ gate pulldown) holds Q1 off at boot and firmware reset — hardware, no firmware dependency
2. PIO program must enforce maximum pulse width (e.g. 2ms hard cap) — hardware-enforced, not just a software limit. A firmware hang must not leave the LED on continuously.
### 11.4 Spinup / spindown
 
**Spinup phases:**
 
1. **Full gyro coverage (0–~500 RPM):** LSM6DSV320X gyro Z provides direct ω integration from rest. No dead zone — the gyro works at 0 RPM where centrifugal signal is completely absent. This replaces the previous feedforward/tangential-axis approach for the low-speed regime entirely. The gyro is the primary ω source during spinup.
2. **Gyro + centrifugal blend (~500–1,500 RPM):** centrifugal signal on the H3LIS331DL outer sensors rises above noise floor (~10G at 500 RPM at 18mm). EKF blends in centrifugal-derived ω as confidence rises with SNR. Gyro weight decreases as centrifugal weight increases. eRPM joins as a third measurement channel.
3. **Full EKF steady state (~1,500+ RPM):** all three ω channels active — gyro, accelerometer array, eRPM. Gyro remains useful as a cross-check and impact recovery anchor even at operating RPM.
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
 
**IMU-A as high-RPM fallback:** During strike mode, IMU-B/C (20mm, 360G at 4,000 RPM) approach their ceiling. EKF automatically reduces measurement weight on IMU-B/C as their readings approach saturation and shifts weight to IMU-A (12mm, 216G at 4,000 RPM, well in-spec) and eRPM. This is a natural consequence of the mixed-radius design — IMU-A has 46% margin remaining where IMU-B/C have only 10%.
 
**RC stick → drift direction:**
- Stick gives desired world-frame translation vector (X, Y)
- Convert to drift direction φ: `φ = atan2(stick_y, stick_x) - θ_current`
- Heading error maps directly to drift direction error — this is why heading quality is everything
### 11.6 Calibration procedure
 
Before first event, on bench:
 
1. **IMU axis verification:** Spin at low RPM (~500), confirm each IMU's radial axis shows centrifugal acceleration outward, tangential axis shows zero (at constant ω). If signs are wrong, fix axis orientation in firmware constants.
2. **IMU position calibration:** Measure actual IMU centroid positions (r_i, φ_i) post-assembly. Store as firmware constants. Small placement errors map directly to heading errors.
3. **H3LIS331DL nonlinearity characterisation:** Spin at 500, 1000, 2000, 3000, 4000 RPM. At each RPM record centrifugal reading vs expected (ω²r/g). Build piecewise linear correction curve per sensor. Critical for IMU-B/C at 20mm operating near 90% of full scale — nonlinearity is worst near saturation. remzakmij discovered this over years of tuning; do it early.
4. **CoR offset calibration:** Spin at known RPM, check if CoR estimate is zero (should be, with no drift input). If nonzero, apply trim correction.
5. **Battery imbalance trim:** Static imbalance from single-pocket battery placement detected as persistent CoR offset. Apply stored trim correction to heading algorithm.
6. **Spindown test:** Verify active braking achieves full stop within 60 seconds from 4,000 RPM.
7. **ELRS failsafe test:** Power robot, establish RC link, kill transmitter, verify motors stop within 1 second.
---
 
## 12. Mass budget
 
### Electronics
 
| Component | Qty | Mass each (g) | Total (g) |
|---|---|---|---|
| D2822 motor | 2 | 44 | 88.0 |
| Repeat AM32 Dual ESC (one board, two channels) | 1 | 6.0 | 6.0 |
| 2S 450mAh 75C LiPo (Tattu) | 1 | ~29 | ~29.0 |
| XIAO RP2350 module | 1 | 3.0 | 3.0 |
| LSM6DSV320X IMU (IMU-A, LGA-14) | 1 | 0.05 | 0.05 |
| H3LIS331DL IMU (IMU-B/C, LGA-16L) | 2 | 0.05 | 0.10 |
| SN74HC595 latch + passives | 1 | ~0.1 | 0.1 |
| Carrier PCB substrate (40×50mm, 1mm) | 1 | ~3.2 | 3.2 |
| AP63205 buck + inductor + passives | 1 | ~0.5 | 0.5 |
| SK9822 LED + AHCT buffers | 1 | ~0.1 | 0.1 |
| Heading LED MOSFET + resistors (Q1) | 1 set | ~0.05 | 0.05 |
| External orange TinySLED module + wires | 1 | ~1.0 | 1.0 |
| ELRS receiver | 1 | ~2 | 2.0 |
| R2ZZ bearings | 2 | 0.7 | 1.4 |
| Fingertech Mini Switch | 1 | 2.15 | 2.15 |
| XT30 connector pair | 1 | ~3 | 3.0 |
| 16 AWG silicone wire | — | — | ~5.0 |
| 28 AWG silicone wire | — | — | ~1.0 |
| M3 fasteners + inserts | — | — | ~5.0 |
| M2 fasteners (wheel hub) | — | — | ~1.0 |
| Loctite + misc | — | — | ~2.0 |
| EVA foam wheels | 2 | ~2 | ~4.0 |
| Wheel coating | — | — | ~1.0 |
| **Electronics subtotal** | | | **~158.1** |
 
### Chassis
 
| Item | Mass (g) |
|---|---|
| PLA+ chassis body | ~292 |
| Ti-6Al-4V weapon tabs (×2) | TBD |
| **Chassis subtotal** | **~292 + tabs** |
 
### Total
 
| | g |
|---|---|
| Electronics | ~158.4 |
| Chassis (excl. tabs) | ~295 |
| **Subtotal** | **~453.4** |
| Target | 454 |
| Margin | ~0.6g |
 
The margin is still very tight. Switching to Repeat Micro AM32 ESCs saves ~10g vs PBB 20A ESCs but the Tattu 450mAh battery adds ~6g vs the Dogcom 350mAh. Net ~4g saved. Weapon tab mass (TBD) remains the main risk. Community feedback strongly recommends the Tattu 450mAh over 350mAh due to uncertain actual current draw — validate on bench early.
 
---
 
## 13. Event calendar
 
| Event | Location | Date | Notes |
|---|---|---|---|
| SEMO Brawl at the Mall | Peoria IL | Jul 18 2026 | Too soon for build completion |
| River City Rumble | Jeffersonville IN | Aug 1 2026 | Possibly achievable as shakedown |
| **Buckeye Bot Bash 2** | Bellefontaine OH | **Aug 29 2026** | **Primary target. Registration opens Jun 26 2026** |
| Midwest Robot Rumble | Grandville MI | Sep 19 2026 | Second event |
 
Check robotcombatevents.com for current registration status.
 
**Action item:** Contact Buckeye Bot Bash EO to confirm meltybrain qualifies as active weapon under their antweight rules. MRCA ruleset does not explicitly ban it but EO confirmation is required before build commitment.
 
---
 
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
 
### Blocking (must resolve before PCB fab)
 
1. **EO confirmation** — Contact Buckeye Bot Bash organizer to confirm meltybrain qualifies as active weapon under MRCA antweight rules. Do not commit to build without this.
2. **H3LIS331DL stock — order immediately** — LCSC stock was 22 units at sensor survey. Order 10+ extras before starting PCB layout.
3. **LSM6DSV320X footprint verification** — LGA-14 2.5×3mm is a different footprint from H3LIS331DL LGA-16L 3×3mm. Verify both footprints exist and are correct in KiCad before ordering PCB. Check LSM6DSV320X axis orientation separately from H3LIS331DL — different pin-1 location and axis convention.
4. **LSM6DSV320X bring-up:** disable I3C on first SPI transaction (write `I2C_I3C_disable=1` to `IF_CFG 0x03`), verify WHO_AM_I, configure accel ±320G + gyro ±4,000 dps at 1,000 Hz ODR. Verify SPI mode 0 works for all three sensors on shared bus.
5. **TinySLED module selection** — Confirm orange 2-3S variant, verify 8.4V tolerance, confirm onboard current limiting.
6. **CRSF inversion** — Check specific ELRS receiver firmware. Non-inverted CRSF preferred. If not, implement in RP2350 PIO.
### Pre-event (must resolve before first match)
 
7. **Wheel diameter** — Measure motor mount height once D2822 is in hand. Wheel radius = mount height + 3-4mm floor clearance. Err toward smaller diameter for better melty ratio per Andrew's Rules.
8. **Weapon tab geometry** — Ti-6Al-4V tab protrusion distance, leading face geometry, attachment method (M3 countersunk through tab into chassis body). Design, source, and machine before chassis print is finalised.
9. **Repeat AM32 Dual physical placement** — 28×20×5mm board needs a home in the chassis that isn't the central electronics zone or battery pocket. Model in CAD before finalising chassis print.
10. **Spindown verification** — Bench test active ESC braking from 4,000 RPM. Verify full stop within 60 seconds.
11. **H3LIS331DL nonlinearity characterisation** — Multi-RPM bench calibration per Section 11.6 step 3. Do before any heading algorithm tuning.
12. **Two-mode RPM validation** — Confirm stable heading at tracking mode (~3,000 RPM), acceptable heading at strike mode (~4,000 RPM). Tune EKF process noise inflation during mode transitions.
13. **Heading LED strobe tuning** — Bench-tune pulse width (start 300µs), phase offset. Verify timing with oscilloscope before arena use.
14. **Power integrity check** — Scope 5V and 3V3 rails during heading LED strobes, DSHOT traffic, and motor spinup. Verify LED pulses don't corrupt IMU reads or reset the XIAO. If noise is seen, add bulk capacitance near the LED MOSFET drain returns.
### Future / Rev 2
 
15. **Spinning IR lidar (Holy Guacamole II)** — 1-2 phototransistor + 940nm IR LED pairs at chassis edge. Reserve D0 GPIO on carrier for IR ADC input.
16. **INA180 / shunt (Rev B consideration)** — If EDT current telemetry latency proves insufficient, add INA180 + inline shunt in a future revision.
17. **ESC BEC characterisation (Rev B consideration)** — Measure BEC voltage, current, and noise under motor load. If confirmed ≥500mA and clean, the AP63205 buck can be removed/DNP'd in Rev B, saving ~0.5g.
18. **EKF tuning constants** — EKF process and measurement noise matrices need empirical tuning. Log IMU and eRPM data during bench sessions, replay in simulation, tune offline.
19. **Impact detection tuning** — EKF impact recovery thresholds need real data. Strike fixed target at known speeds, record gyro/eRPM/accel responses, set thresholds empirically.
---
 
*Last updated: v1.4 — SN74HC595 latch replaces MCP23S17; board is 40×50mm rectangular; heading LED simplified to single orange TinySLED + Q1; piezo impact sensor removed entirely; impact detection uses gyro + eRPM + accel residual only; pin table matches circuit.py Rev A.*
