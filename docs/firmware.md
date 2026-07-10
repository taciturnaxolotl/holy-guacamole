# Holy Guacamole — Firmware & Simulator (running doc)

**Document type:** Running engineering doc for the *as-built* firmware and the
SITL digital twin. Updated as code lands.
**Scope:** What is actually implemented in `firmware/`, how to build/test it,
and the simulator fidelity model. For hardware see `spec.md` (carrier PCB) and
`braindump.md` (design research / rationale).

> `spec.md` is the carrier-PCB spec and is not affected by firmware/sim work.
> `braindump.md` is the design/research record and describes *intended* designs
> (some ahead of the code). This doc tracks *what the code does today* and the
> numbers the twin is anchored to.

---

## 1. Status snapshot

| Area | State |
|---|---|
| Math (`linalg`) | implemented, unit-tested |
| Estimation (`ekf`, `meas_model`, `imu_geom`, `imu_convert`) | implemented, tested; **reduced 3-state filter** (see §4) |
| `accel_cal` | **wired** into the shared SI path (`app_sensor_tick_si` → `accel_cal_apply`, outer H3LIS channels); unit-tested + validated end-to-end. No-op until a table is loaded |
| Control (`pid`, `drift`) | implemented; sinusoidal + square modulation |
| Safety (`watchdog`, `rc_health`, `battery`) | implemented; dual-core spinlock watchdog |
| App glue (`control_loop`) | implemented; shared by firmware and sim |
| SITL sim | **hand-rolled plant (Box2D dropped), realistic IMU, scenario harness** — see §7 |
| Drivers (`imu_spi`, `dshot`, `crsf`, `latch`) | in progress |

---

## 2. Build & test quickref

All commands run inside the Nix dev shell.

```bash
# Firmware (RP2350 / Pico 2)
nix develop --command bash -c \
  'cmake -B build -DPICO_PLATFORM=rp2350 -DPICO_BOARD=pico2 && cmake --build build -j'

# Unit tests (host)
nix develop --command bash -c \
  'ctest --test-dir build-tests --output-on-failure'

# Interactive SITL sim (raylib window)
nix develop --command bash -c \
  'cmake -B build-sim -S sim && cmake --build build-sim'
```

Tests live in `firmware/tests/`: `test_linalg`, `test_ekf`, `test_drift`,
`test_sim_convergence`, and `test_scenarios` (closed-loop digital-twin
scenarios). All build with the host compiler under `-Wall -Wextra -Werror`.

---

## 3. Repo / module map

```
firmware/src/
  main.c                 app entry, dual-core bringup, arming logic
  app/control_loop.{c,h} HW-free per-tick logic shared by firmware AND sim:
                         app_sensor_tick_si (EKF) + app_control_tick (drift)
  estimation/
    ekf.{c,h}            reduced 3-state EKF (theta, omega, alpha)
    meas_model.{c,h}     7-row measurement model + saturation flags
    imu_geom.{c,h}       sensor positions + shared physical constants
    imu_convert.{c,h}    raw counts -> SI
    accel_cal.{c,h}      accel calibration
  control/
    drift.{c,h}          sinusoidal/square thrust modulation (drift_mod_t)
    pid.{c,h}            RPM PID
  safety/
    watchdog.{c,h}       dual-core spinlock watchdog
    rc_health.{c,h}      link-alive tracking
    battery.{c,h}        VBAT EMA + warn/halt thresholds
  imu/    imu_spi, latch     SPI + SN74HC595 chip-select latch
  dshot/  dshot + PIO        bidir DSHOT600
  crsf/   crsf               ELRS RC input

firmware/sim/
  plant.{c,h}            physics plant (rigid disc, arena)
  imu_synth.{c,h}        truth-state -> noisy/saturated measurement vector
  robot_sim.{c,h}        headless pure-angular kinematic sim
  drive.c                interactive raylib test-drive harness

firmware/tests/
  test_scenarios.c       closed-loop assert-based scenarios (wired to CTest;
                         there is no sim/scenario.c — it lives here)
```

**Key architectural rule:** the estimator + controller live in
`app/control_loop.c` and are called *identically* by the firmware (`main.c`,
split across two cores) and the sim. The sim never reimplements control logic;
it only supplies sensor readings and consumes motor throttles. This is what
makes the twin meaningful.

---

## 4. Estimation — as-built vs aspirational

**As-built (code today):** a reduced EKF with state `x = [theta, omega, alpha]`
(`meas_model.h`). Heading is dead-reckoned from `omega`; it is *not* directly
observable from body-frame accelerometers in steady spin (the fundamental
meltybrain observability limit). Measurement is a fixed 7-row set:

```
per IMU:  a_radial = omega^2 * r      (centripetal, outward +)
          a_tangential = alpha * r    (Euler term)
IMU-A only: gyro_z = omega
```

**Aspirational (braindump §11.3):** a 7-state angular-momentum filter
`[H_z, theta, omega, alpha, jerk, cor_x, cor_y]` with CoR estimation, jerk
augmentation, and eRPM fusion. Not yet implemented. Tracked as future work; the
twin is being built so the jump from 3-state to 7-state can be validated
against ground truth.

---

## 5. Anchored physical parameters (single source of truth)

Real numbers for this build. The sim `plant_params_t` defaults derive from
this table; change here and in the struct together.

| Parameter | Value | Notes |
|---|---|---|
| Mass | 0.454 kg | 1 lb antweight |
| Disc body radius `R_body` | 0.085 m | 170 mm body diameter (mass) |
| Weapon-tip radius `R_tip` | 0.115 m | 230 mm tip-to-tip; **collision radius** |
| Moment of inertia `I` | `k·m·R_body²`, k≈0.55 → ~1.8e-3 kg·m² | k tunable (mass distribution) |
| Thrust lever `r_w` | ~0.055–0.06 m | effective drive-wheel lever from centre |
| Normal RPM | 2600–2750 rpm (272–288 rad/s) | tracking mode, ~0.44 throttle |
| Strike/burst RPM | 3750–4000 rpm (393–419 rad/s) | pre-attack punch, ~0.65 throttle |
| Full-throttle terminal ω | ~644 rad/s (~6150 rpm) | headroom above combat RPM so drift modulation doesn't clip |
| Battery | 2S 350 mAh | |
| Arena | ~1.8 m square (5.9 ft), ¼" polycarbonate walls | half-extent 0.9 m; matches braindump ~6 ft antweight arena |

### IMU array

| IMU | Part | Radius | Angle | Gyro |
|---|---|---|---|---|
| A (inner) | LSM6DSV320X | 12 mm | 0° | yes |
| B (outer) | H3LIS331DL | 18 mm | 90° | no |
| C (outer) | H3LIS331DL | 18 mm | 210° | no |

### Sensor characteristics (from datasheets)

| Channel | Range | Quant (LSB) | Noise σ (est.) | Rails at |
|---|---|---|---|---|
| LSM6 hi-g accel | ±320 g | 9.77 mg = 0.096 m/s² | ~0.25–0.5 m/s² | 313 g |
| H3LIS accel | ±400 g | 195 mg = **1.91 m/s²** | **~2.5 m/s²** | 392 g |
| LSM6 gyro | ±4000 dps | 140 mdps = 0.0024 rad/s | ~0.001 rad/s | **69.8 rad/s** |

ODR / bus: H3LIS ≤ 1 kHz, LPF cutoffs 37/74/292/780 Hz, **no FIFO, INT
unconnected → must poll**. LSM6 ≤ 7.68 kHz. Shared SPI ≤ 10 MHz, one CS at a
time.

### Centripetal load at the sensors (a = ω²·r)

| Sensor | r | normal (2700 rpm) | burst (4000 rpm) | headroom |
|---|---|---|---|---|
| LSM6 inner | 12 mm | 98 g | 215 g | fits ±320 g |
| H3LIS outer | 18 mm | 147 g | 322 g | fits ±400 g (0.98·400=392) |

The mounting radii are chosen so the **accelerometers never rail during normal
play** — saturation only bites on impact spikes or overspin.

---

## 6. Twin findings (why the sim is being rebuilt)

1. **The gyro is pinned to its rail during every combat spin.** Spin is
   272–419 rad/s; the LSM6 gyro saturates at 69.8 rad/s (±4000 dps). Above
   ~670 rpm the gyro is railed by 4–6×. The old sim modeled the gyro as *never*
   saturating, feeding the EKF a perfect gyro that will not exist on hardware.
   Reality: `omega` comes from the accel centripetal channel at speed; the gyro
   only lives during spin-up start and shutdown, and as an impact anchor.
2. **The two accel families are very different.** Outer H3LIS are ~6–8× noisier
   and quantize in ~2 m/s² steps; the inner LSM6 is clean. The EKF's R matrix
   (and the sim's per-channel noise) should reflect that, not use one flat σ.
3. **ODR mismatch.** Outer sensors sample-and-hold at ≤1 kHz through a 292–780 Hz
   LPF with no FIFO (polled), giving ~15–22 samples/rev at speed and smearing
   transients. The inner sensor runs much faster.
4. **Wall rebound was black-box.** The old plant used Box2D's generic contact
   solver at RPMs and per-step rotations it was never designed for, with
   untuned restitution and no explicit spin↔translation coupling.
5. **Uncorrected H3LIS nonlinearity loses heading within ~3 s at combat RPM.**
   With the realistic sensor model, the ~5% full-scale droop biases omega
   enough that heading walks a full 180° in 3 s (2700 rpm). Noise alone
   (nonlinearity removed) gives ~13° drift at 2700 rpm, ~54° at 4500 rpm over
   the same window. So `accel_cal` is not optional — the nonlinearity curve is
   the single biggest determinant of heading hold. Wired: the sim rails the
   gyro at ±4000 dps and `meas_saturation_flags` now drops a railed gyro
   (inflates R), so the EKF leans on the accel centripetal channel at speed
   exactly as the hardware must; steady-state tests spin up from rest so the
   gyro can bootstrap omega's sign below 670 rpm before it rails.

---

## 7. SITL simulator

### 7.1 Architecture

The sim composes the **real** `app_` estimator/controller with a physics plant
and a synthetic IMU. Two front-ends share one plant + one sensor model:

- `robot_sim.c` — headless pure-angular kinematics (deterministic filter tests).
- `drive.c` — interactive raylib top-down view (hand-driving, watch heading lock).
- `tests/test_scenarios.c` — scripted assert-based regression scenarios → CTest.

### 7.2 Decision: hand-rolled plant (Box2D dropped)

The disc is a circle whose Box2D orientation is deliberately ignored (heading is
`∫omega`), so Box2D earned little and fought us at high RPM. The rebuilt plant is
a hand-rolled 2D rigid body: state `{x, y, vx, vy, theta, omega}`, semi-implicit
integration, heading integrated trapezoidally to match the EKF's midpoint
predict. Analytic circle-vs-square collision. Fully deterministic; removes the
high-RPM solver artifacts. Tradeoff: no free broad-phase if opponents/obstacles
are added later (revisit then).

All plant constants move into a `plant_params_t` struct so tuning lives in one
place and the harness can sweep it.

### 7.3 Wall contact model (the headline fix)

The disc **body** (radius 85 mm) gets a continuous circle contact: normal
bounce (restitution `e`), tangential **skitter** from rim friction, and **spin
bleed**, all from one friction-cone impulse.

On top of that, the two **weapon tabs** reach out to the 115 mm tip radius and
are modelled as point contacts. A fast-spinning tab striking a wall applies the
full rigid-body impulse (translation + rotation coupled through the lever arm),
so the robot is thrown off the wall and bleeds spin. Consequence: a **spinning**
bot driven into a wall gets flung clear (tabs bite, then it skitters away),
while a **dead** bot just pins and rests — it can't sit against the wall while
the weapon is live, matching the real robot. (A perfectly balanced bot placed
exactly grazing at rest is the one idealized case that still sits; real driving
never lands there.)

Defaults: `e_wall=0.35`, `μ_wall=0.5`, 2 tabs 180° apart.

### 7.4 Motor + drivetrain model

- Torque-speed curve per drive wheel: `τ = throttle·τ_stall·(1 − ω·r_w/v_free)`
  (back-EMF rolloff), so terminal RPM is set by the motor, not by fudged drag.
- **Full-throttle terminal ~6150 rpm**, deliberately well above combat speed.
  Combat RPM is reached at partial throttle (~0.44 for 2700, ~0.65 for 4000),
  which leaves headroom for the drift modulation. Setting the terminal at
  4000 rpm (the earlier mistake) meant combat RPM needed ~full throttle, so the
  modulation clipped and translation collapsed above ~3000 rpm. With headroom,
  translation is strong and roughly flat across 1000–4000 rpm.
- First-order **ESC lag** on commanded → applied throttle; spin-up time
  constant ~0.7 s (~1 s to 3000 rpm).
- Floor friction is **Coulomb** (`μ·m·g`), not linear viscous — this is why the
  arrow-key response feels less springy than the old Box2D build, and is the
  more realistic behaviour.

**Validated (§7.2–7.4, host smoke test):**

| Metric | Result | Target |
|---|---|---|
| Full-throttle terminal | 4001 rpm | ~4000 |
| Time to 3000 rpm | 0.99 s | < 2 s |
| 0.67-throttle terminal | 2681 rpm | ~2700 |
| Back-EMF spindown to 5% | 2.12 s | (free, no brake) |
| Heading-synced drift, A=0.30, 2 s | 1.08 m | > 0 |

Two emergent (correct) behaviours the twin now reproduces for free:

- **Constant asymmetric throttle produces zero translation** — a melty only
  drifts when the asymmetry is modulated in sync with heading. The plant
  enforces this; you cannot cheat drift open-loop.
- **ESC lag phase-shifts the drift direction** (~40° at cruise from
  `atan(2π·f_rev·τ_esc)`), so commanded `phi` maps 1:1 to world direction with
  a constant offset. This is exactly the `drift_phase`/`heading_trim` constant
  the firmware calibrates on the bench. `τ_esc` must stay well below the
  revolution period or the modulation is filtered out (why authority falls at
  very high RPM, matching community reports).

### 7.5 Sensor realism (`imu_synth`, datasheet-anchored)

- **Gyro saturation at ±4000 dps** (new shared `GYRO_FULL_SCALE`). The EKF
  finally faces a railed gyro during spin.
- **Gyro bias + in-run random walk** — the heading killer; stresses the filter.
- **Per-sensor accel noise + quantization** (outer ≈2.5 m/s² + 1.91 LSB, inner
  ≈0.3 m/s² + 0.096 LSB) instead of one flat σ.
- **Accel scale-factor / misalignment / zero-g offset** + mounting radius/angle
  perturbation vs nominal, so `accel_cal` has something real to solve.
- **Spin-synchronous vibration** (once-per-rev + harmonics) on top of white noise.
- **Per-sensor ODR sample-and-hold** (H3LIS 1 kHz + LPF, LSM6 fast) + optional
  dropped-sample for the pollable, FIFO-less outer chips.
- Everything behind flags with a seeded PRNG so tests stay deterministic.

The interactive `drive` tool uses a **calibrated** sensor (nonlinearity off),
because the real robot removes it with `accel_cal` and the SITL SI path doesn't
run that correction. Left on, the uncorrected bias walks heading and noticeably
worse while translating (the drift modulation ripples omega, so the
amplitude-dependent bias no longer trims out).

### 7.6 Scenario harness

`tests/test_scenarios.c` composes the plant + the real `app_` estimator and
controller, runs headless, and asserts on emergent behaviour. Wired into CTest
(`test_scenarios`), deterministic (seeded). Current scenarios, all passing:

1. **Spin-up** — full throttle reaches 3700–4100 rpm, EKF omega tracks within
   5%, and the gyro is confirmed pinned at its rail.
2. **Cruise drift** — commanding a stick direction at ~2700 rpm translates the
   robot (>0.1 m) while omega stays locked within 3% (calibrated sensor).
3. **Wall skitter** — a spinning disc coasted into a wall bounces (v_n reverses),
   skitters along it (tangential velocity appears from spin with motors off),
   and bleeds RPM.
4. **Nonlinearity matters** — uncorrected H3LIS nonlinearity walks heading far
   worse than the calibrated case; guards that `accel_cal` is mandatory.
5. **Burst saturation** — at overspeed the gyro and both outer H3LIS radials
   rail while the inner LSM6 accel stays in-spec (the mixed-radius payoff).

Deferred: per-sensor ODR sample-and-hold / dropped samples (H3LIS 1 kHz, no
FIFO) and `accel_cal` correction inside the SI estimation path.

### 7.7 Decisions in effect

- **Gyro-rail: expose-first.** The sim will model the real ±4000 dps rail even
  though it may stress/break the current EKF. That is the sim doing its job;
  any EKF changes are tracked as follow-up, not bundled into the sim work.
- **Starting tuning guesses:** `k=0.55`, `e_wall=0.35`, `μ_wall=0.5`, floor
  `μ≈0.4`. All one-line tunable in `plant_params_t`.
- **Build sequence:** plant → walls → motor → sensors → harness, testing each.

---

## 8. Open discrepancies / TODO

- [ ] EKF is 3-state as-built vs 7-state in braindump §11.3. Reconcile or
      re-scope the braindump when the augmented filter lands.
- [ ] Chassis geometry: braindump §4/§5 use 150 mm OD / 75 mm edge and are
      **out of date**. Current build: 170 mm body diameter (85 mm radius,
      carries mass), 230 mm tip-to-tip (115 mm weapon-tip collision radius).
      Refresh braindump G-load / tip-speed calcs to match.
- [x] Drift modulation mode is a **build-time flag** (`DRIFT_DEFAULT_MODE` in
      `control_loop.h`): flip the line or pass `-DDRIFT_DEFAULT_MODE=DRIFT_MOD_SQUARE`.
      No runtime toggle, by request.
- [x] `accel_cal` wired into the SI estimation path and validated end-to-end
      (loading the inverse curve recovers heading with nonlinearity on).
      Remaining: per-sensor curves (B and C share one today) and a bench
      routine to fill the table from a spin-up sweep.
- [x] Core 1 PID now uses the **measured** loop period, not the constant
      `CONTROL_DT` (that core also runs CRSF/DSHOT/telemetry, so the true
      period is longer). Matters when RPM PID is bench-tuned.
- [ ] Sim ODR fidelity: per-sensor sample-and-hold + dropped samples for the
      1 kHz, FIFO-less H3LIS outer accels (deferred from §7.5).
- [x] Box2D removed from `sim/CMakeLists.txt` and `flake.nix` (hand-rolled
      plant landed).

### Dead / unused code (flagged during code review)

These are compiled or defined but do nothing today. Each is either
scaffolding for a planned feature or leftover that should be pruned. Left
as-is they cost build size, reader confusion, and (for the `-Werror` host
build) latent warnings. Decide per item: **wire it or delete it.**

- **`latch_shadow` + `latch_get_image()` are dead.** `latch_load` caches the
  shadow byte but the only reader (`latch_get_image`, `static`) is never
  called, so the cache buys nothing. It exists for the braindump §11.2
  optimization (a single latch write that de-asserts the previous CS and
  asserts the next simultaneously), but `latch_select` instead does
  disable → load → enable every transaction, blanking outputs between reads.
  That is safe and simple; if we keep it, delete the unused shadow machinery.
- **`hardware_dma` + `hardware_irq` are linked but unused.** There is no DMA
  or IRQ code anywhere; core 0 captures IMUs with **blocking** SPI in a
  `busy_wait`-paced 1 kHz loop. Braindump §11.2's "DMA-driven burst reads →
  interrupt → process batch" is aspirational, not as-built. Drop the link
  deps until DMA lands, and note in the braindump that capture is currently
  polled.
- **CRSF `link_quality` / `rssi_dbm` are parsed but never read.** Arming uses
  only link-alive timeout + `rc_health` + battery. Fine to keep for future
  telemetry/LED use, but nothing consumes them yet.
- **eRPM telemetry is decoded but not fused.** `dshot_read_telemetry` runs and
  `rpm` is printed in the status line, but the EKF has no eRPM measurement row
  (consistent with the 3-state filter). This is expected today; listed so the
  gap is explicit when the 7-state / eRPM-fusion work starts.

### Firmware not yet started (braindump requires, no code exists)

Called out so the braindump's "firmware requirement" language isn't mistaken
for as-built:

- **Heading LED strobe** (braindump §11.3b). `PIN_HEAD_LED` is defined in
  `hw_pins.h` but nothing drives it. The mandated PIO hard pulse-width cap
  (fire-safety) is unimplemented.
- **SK9822 status LED + `LED_OE_N` gating** (braindump §11.2). `LATCH_BIT_LED_OE_N`
  is defined but never asserted; no LED frame is ever clocked.
