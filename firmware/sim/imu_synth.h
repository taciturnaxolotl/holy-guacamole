#pragma once

/*
 * Shared IMU reading synthesis: turn a known angular state into the
 * measurement vector the IMU array would report, including Gaussian
 * noise and sensor saturation.
 *
 * Used by both the headless robot_sim (deterministic convergence tests)
 * and the interactive Box2D plant, so the sensor model lives in exactly
 * one place.
 */

#include <stdint.h>
#include <stdbool.h>
#include "math/linalg.h"

typedef struct {
    uint64_t rng;              /* xorshift state (seedable, reproducible) */
    float accel_noise_sigma;   /* m/s^2 per accel axis */
    float gyro_noise_sigma;    /* rad/s */
    bool  enable_noise;
    bool  enable_saturation;
} imu_synth_t;

/* Initialize with datasheet-scale noise and a PRNG seed. */
void imu_synth_init(imu_synth_t *s, uint64_t seed);

/* Fill z (MEAS_DIM x 1) from angular velocity and acceleration. */
void imu_synth_read(imu_synth_t *s, float omega, float alpha, mat_t *z);
