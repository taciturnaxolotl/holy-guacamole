#pragma once

/*
 * IMU array geometry and shared physical constants.
 *
 * Positions are from the spec: one inner LSM6DSV320X (with gyro) and
 * two outer H3LIS331DL. Each chip is mounted with its X axis pointing
 * radially outward from the rotation centre and its Y axis tangential
 * (CCW-positive). These constants are shared config used by both the
 * physics simulator (forward model) and the EKF measurement model.
 *
 * All units are SI: metres, rad/s, rad/s^2, m/s^2.
 */

#include <stdbool.h>

#define IMU_COUNT_GEOM 3

/* Standard gravity, for g <-> m/s^2 conversion at the sensor boundary. */
#define G_TO_MS2 9.80665f

/* H3LIS331DL full-scale ceiling (outer sensors). Radial readings above
 * this rail are clipped in hardware and must be treated as invalid. */
#define H3LIS_FULL_SCALE_G   400.0f
#define H3LIS_FULL_SCALE_MS2 (H3LIS_FULL_SCALE_G * G_TO_MS2)

typedef struct {
    float radius_m;    /* distance from rotation centre */
    float angle_rad;   /* mounting angle around the disc (for CoR/linear terms) */
    bool  has_gyro;    /* true only for the inner LSM6DSV320X */
} imu_geom_t;

/* Indexed IMU_A=0, IMU_B=1, IMU_C=2 to match imu_spi.h. */
extern const imu_geom_t imu_geom[IMU_COUNT_GEOM];
