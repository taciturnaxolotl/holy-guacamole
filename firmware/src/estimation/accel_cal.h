#pragma once

#include <stdbool.h>
#include "math/linalg.h"

/*
 * Per-accelerometer nonlinearity correction tables.
 *
 * The H3LIS331DL sensors are not perfectly linear across their +/-400G
 * range: near full scale the reported value deviates from true
 * acceleration, and the deviation differs sensor-to-sensor (unit MEMS
 * variation, mount tilt, actual vs nominal radius). Each IMU therefore
 * gets its OWN piecewise-linear curve, built during bench calibration
 * (spin at known RPMs, compare measured centrifugal to expected omega^2 r).
 *
 * Correction is multiplicative:  corrected = raw * get(imu, raw_g)
 *
 * Table format per IMU: pairs of (raw_g, correction_factor), sorted by
 * raw_g, linearly interpolated, endpoints held outside the range.
 */

#define ACCEL_CAL_MAX_POINTS 8  /* max calibration points per IMU */

/* IMU indices, matching the measurement-vector layout (A = inner
 * LSM6DSV320X, B/C = outer H3LIS331DL). */
enum {
    ACCEL_CAL_IMU_A = 0,
    ACCEL_CAL_IMU_B = 1,
    ACCEL_CAL_IMU_C = 2,
    ACCEL_CAL_IMUS  = 3,
};

/* Clear every table (no correction). */
void accel_cal_init(void);

/* Add a calibration point for one IMU. Points need not be added in order;
 * the table is kept sorted. Returns false if that IMU's table is full or
 * imu is out of range. */
bool accel_cal_add(int imu, float raw_g, float correction_factor);

/* Correction factor for a raw G reading on one IMU. Returns 1.0 if that
 * IMU has no calibration data. */
float accel_cal_get(int imu, float raw_g);

/* Number of points stored for one IMU. */
int accel_cal_count(int imu);

/* Apply each IMU's stored correction in place to its accelerometer channels
 * of a measurement vector z (radial + tangential). No-op for any IMU with
 * an empty table, so it is safe to call always. The gyro channel is left
 * untouched. */
void accel_cal_apply(mat_t *z);

/* Clear all tables. */
void accel_cal_clear(void);
