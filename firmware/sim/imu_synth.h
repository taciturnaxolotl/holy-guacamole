#pragma once

/*
 * Shared IMU reading synthesis: turn a known angular state into the
 * measurement vector the IMU array would report, corrupted with the
 * imperfections the EKF must survive on real hardware.
 *
 * Datasheet-anchored (LSM6DSV320X inner + 2x H3LIS331DL outer). Models:
 *   - per-sensor white noise (outer H3LIS ~6-8x noisier than inner LSM6)
 *   - per-sensor quantization (coarse ~1.9 m/s^2 LSB on the outer accels)
 *   - hard rails: accel full-scale AND the gyro at +/-4000 dps (pinned
 *     during any combat spin)
 *   - gyro bias + in-run random walk (the heading-integration killer)
 *   - H3LIS nonlinearity that droops toward saturation (what accel_cal
 *     is built to correct)
 *   - spin-synchronous vibration (once-per-rev + 2nd harmonic)
 *
 * Used by both the headless robot_sim (deterministic convergence tests)
 * and the interactive plant, so the sensor model lives in one place. All
 * corruption is seeded (reproducible) and each source can be toggled.
 */

#include <stdint.h>
#include <stdbool.h>
#include "math/linalg.h"

typedef struct {
    uint64_t rng;              /* xorshift state (seedable, reproducible) */

    /* Per-family white-noise sigma (m/s^2 for accel, rad/s for gyro). */
    float accel_inner_sigma;   /* LSM6 high-g */
    float accel_outer_sigma;   /* H3LIS */
    float gyro_sigma;

    /* Per-family quantization step (LSB in SI units); 0 disables. */
    float accel_inner_lsb;
    float accel_outer_lsb;
    float gyro_lsb;

    /* Gyro bias state (rad/s) and in-run random-walk drive
     * (rad/s per sqrt(s)). */
    float gyro_bias;
    float gyro_bias_walk;

    /* H3LIS nonlinearity: reading *= (1 - knl*(reading/FS)^2). */
    float outer_nonlinearity;

    /* Spin-synchronous vibration amplitude on accel channels (m/s^2). */
    float vibration;
    float vib_phase;           /* internal accumulator (= integral of omega) */

    /* Toggles. */
    bool enable_noise;
    bool enable_saturation;
    bool enable_bias;
    bool enable_nonlinearity;
    bool enable_vibration;
    bool enable_quant;
} imu_synth_t;

/* Initialize with datasheet-scale, realistic defaults and a PRNG seed.
 * A fixed gyro bias is drawn from the seed at init. */
void imu_synth_init(imu_synth_t *s, uint64_t seed);

/* Fill z (MEAS_DIM x 1) from angular velocity, acceleration, and the
 * timestep dt (used for gyro bias random-walk and vibration phase). */
void imu_synth_read(imu_synth_t *s, float omega, float alpha, float dt, mat_t *z);
