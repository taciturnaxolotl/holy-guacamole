#pragma once

/*
 * Reduced heading EKF: state x = [theta, omega, alpha].
 *
 * Predict: constant-alpha kinematic model.
 *   theta += omega*dt + 0.5*alpha*dt^2
 *   omega += alpha*dt
 *   alpha  = alpha            (driven only by process noise)
 *
 * Update: fuses the 3-IMU radial/tangential accelerometer readings and
 * the inner gyro (see meas_model.h). Uses Joseph-form covariance update
 * for float32 numerical robustness, and inflates measurement noise on
 * saturated outer-sensor channels so railed readings don't pull omega.
 *
 * All state is held in the ekf_t struct; no globals, no allocation.
 */

#include "math/linalg.h"
#include "meas_model.h"

typedef struct {
    mat_t x;   /* state, ST_DIM x 1 */
    mat_t P;   /* covariance, ST_DIM x ST_DIM */

    /* Process noise (per-state variance rates). */
    float q_theta;
    float q_omega;
    float q_alpha;

    /* Base measurement noise variances. */
    float r_accel;   /* per accelerometer axis */
    float r_gyro;    /* gyro Z */

    /* Factor by which R is multiplied for a saturated channel. */
    float sat_inflation;
} ekf_t;

/* Initialize with sensible defaults and a given starting omega guess
 * (rad/s; use 0 for spinup from rest). Covariance starts diagonal-large. */
void ekf_init(ekf_t *e, float omega0);

/* Prediction step over dt seconds. */
void ekf_predict(ekf_t *e, float dt);

/* Measurement update. z is MEAS_DIM x 1 in SI units (m/s^2, rad/s).
 * Saturated radial channels are automatically down-weighted. */
void ekf_update(ekf_t *e, const mat_t *z);

/* Convenience accessors. */
float ekf_theta(const ekf_t *e);
float ekf_omega(const ekf_t *e);
float ekf_alpha(const ekf_t *e);

/* Wrap heading into [0, 2*pi). */
float ekf_heading_wrapped(const ekf_t *e);

/* Fuse an external heading measurement (e.g., from RSSI edge PLL).
 * r_theta is the measurement noise variance in rad^2; use a large
 * value when confidence is low. This directly observes ST_THETA,
 * which is otherwise unobservable from IMU-only measurements. */
void ekf_update_heading(ekf_t *e, float theta_meas, float r_theta);
