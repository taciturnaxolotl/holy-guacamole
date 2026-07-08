#pragma once

/*
 * Forward physics simulator for a spinning meltybrain. HOST-ONLY:
 * generates the accelerometer/gyro readings each IMU would report
 * from a known true state, so the EKF can be validated with no
 * hardware.
 *
 * The true state is integrated in double precision (host has no FPU
 * constraint) so it stays an accurate reference; emitted measurements
 * are downcast to float32 to match the target sensor path.
 *
 * Deliberately derived from rigid-body kinematics, then corrupted with
 * Gaussian noise and sensor saturation the EKF does NOT model. If the
 * filter only worked on its own clean equations that would be a
 * tautology; feeding it noise + rail-clipping breaks that.
 */

#include <stdint.h>
#include <stdbool.h>
#include "math/linalg.h"
#include "imu_synth.h"

typedef struct {
    /* True state (double for an accurate ground-truth reference). */
    double theta;
    double omega;
    double alpha;

    imu_synth_t synth;   /* shared IMU reading model (noise + saturation) */
} robot_sim_t;

/* Initialize truth at omega0 (rad/s), zero heading, given PRNG seed.
 * Noise and saturation on by default with datasheet-scale sigmas. */
void sim_init(robot_sim_t *s, double omega0, uint64_t seed);

/* Advance the true state by dt seconds under commanded angular
 * acceleration alpha_cmd (rad/s^2). Use 0 for steady spin. */
void sim_step(robot_sim_t *s, double alpha_cmd, double dt);

/* Apply an instantaneous angular-velocity change (impact model). */
void sim_kick_omega(robot_sim_t *s, double domega);

/* Produce the MEAS_DIM measurement vector the IMU array would report
 * from the current true state, including noise and saturation. */
void sim_read(robot_sim_t *s, mat_t *z);
