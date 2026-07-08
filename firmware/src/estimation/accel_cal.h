#pragma once

#include <stdbool.h>

/*
 * Accelerometer nonlinearity correction table.
 *
 * The H3LIS331DL sensors are not perfectly linear across their ±400G
 * range. At high G (near saturation), the reported value deviates from
 * true acceleration. This module stores a piecewise-linear correction
 * curve built during bench calibration (spin at known RPMs, compare
 * measured centrifugal to expected ω²r).
 *
 * The correction is applied as a multiplicative factor:
 *   corrected = raw * get_accel_correction(raw_g)
 *
 * Table format: pairs of (raw_g, correction_factor), sorted by raw_g.
 * Linear interpolation between points. Outside the table range, the
 * nearest endpoint factor is used.
 */

#define ACCEL_CAL_MAX_POINTS 8  /* max calibration points */

/* Initialize with an empty table (no correction). */
void accel_cal_init(void);

/* Add a calibration point. Points need not be added in order; the table
 * is kept sorted. Returns false if table is full. */
bool accel_cal_add(float raw_g, float correction_factor);

/* Get the correction factor for a given raw G reading. Returns 1.0 if
 * no calibration data exists. */
float accel_cal_get(float raw_g);

/* Number of calibration points currently stored. */
int accel_cal_count(void);

/* Clear all calibration data. */
void accel_cal_clear(void);
