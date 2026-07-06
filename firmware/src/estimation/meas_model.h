#pragma once

/*
 * EKF measurement model for the reduced heading filter.
 *
 * State (reduced):  x = [theta, omega, alpha]
 *   theta - heading angle (rad), integrated from omega; NOT directly
 *           observable from body-frame accelerometers in steady spin.
 *   omega - angular velocity (rad/s)
 *   alpha - angular acceleration (rad/s^2)
 *
 * Measurement (7 rows), for each IMU in its own body frame:
 *   radial axis (X):     a_x = omega^2 * r     (centrifugal, outward +)
 *   tangential axis (Y): a_y = alpha  * r      (Euler term)
 *   gyro Z (IMU-A only): omega
 *
 * theta does not appear in any measurement equation: the centrifugal
 * vector is constant in the body frame, so heading is dead-reckoned
 * from omega. This is the fundamental meltybrain observability limit.
 */

#include <stdbool.h>
#include "math/linalg.h"

/* Reduced state layout. */
enum { ST_THETA = 0, ST_OMEGA = 1, ST_ALPHA = 2, ST_DIM = 3 };

/* Measurement layout (fixed 7-row set for the 3-IMU array). */
enum {
    MEAS_A_RADIAL = 0,
    MEAS_A_TANGENTIAL = 1,
    MEAS_A_GYRO = 2,
    MEAS_B_RADIAL = 3,
    MEAS_B_TANGENTIAL = 4,
    MEAS_C_RADIAL = 5,
    MEAS_C_TANGENTIAL = 6,
    MEAS_DIM = 7,
};

/* Predict the measurement vector z (MEAS_DIM x 1) from state x (ST_DIM x 1). */
void meas_predict(const mat_t *x, mat_t *z);

/* Measurement Jacobian H (MEAS_DIM x ST_DIM) evaluated at state x. */
void meas_jacobian(const mat_t *x, mat_t *H);

/* Flag which radial measurement rows would be saturated at the given
 * omega (outer H3LIS sensors clip at +/-400g). saturated[] has MEAS_DIM
 * entries; only radial rows can be set true. The EKF inflates R for
 * flagged rows instead of trusting a railed reading. */
void meas_saturation_flags(float omega, bool saturated[MEAS_DIM]);
