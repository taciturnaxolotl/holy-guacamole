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
#include <math.h>

#define IMU_COUNT_GEOM 3

/* Standard gravity, for g <-> m/s^2 conversion at the sensor boundary. */
#define G_TO_MS2 9.80665f

/* H3LIS331DL full-scale ceiling (outer sensors). Radial readings above
 * this rail are clipped in hardware and must be treated as invalid. */
#define H3LIS_FULL_SCALE_G   400.0f
#define H3LIS_FULL_SCALE_MS2 (H3LIS_FULL_SCALE_G * G_TO_MS2)

/* LSM6DSV320X full-scale ceiling (inner sensor). */
#define LSM6_FULL_SCALE_G    320.0f
#define LSM6_FULL_SCALE_MS2  (LSM6_FULL_SCALE_G * G_TO_MS2)

/* LSM6DSV320X gyro full-scale ceiling (inner sensor, ONLY gyro in the
 * array). At meltybrain RPM the spin far exceeds this, so the gyro is
 * pinned to its rail during combat and is only linear below ~670 rpm
 * (spin-up start / shutdown / impact recovery). Heading-rate at speed
 * must come from the accelerometer centripetal channel, not the gyro. */
#define GYRO_FULL_SCALE_DPS  4000.0f
#define GYRO_FULL_SCALE_RADS (GYRO_FULL_SCALE_DPS * (float)M_PI / 180.0f)

/* Saturation detection threshold as fraction of full scale. Readings at
 * or above this fraction are considered railed. Shared by EKF and sim
 * so both use the same boundary. */
#define SATURATION_FRAC 0.98f

/* Wrap angle into [0, 2*pi). Single canonical implementation to prevent
 * drift between EKF, plant, and visualization. */
static inline float wrap_0_2pi(float a) {
    float two_pi = 2.0f * (float)M_PI;
    a = fmodf(a, two_pi);
    if (a < 0.0f) a += two_pi;
    return a;
}

typedef struct {
    float radius_m;    /* distance from rotation centre */
    float angle_rad;   /* mounting angle around the disc (for CoR/linear terms) */
    bool  has_gyro;    /* true only for the inner LSM6DSV320X */
} imu_geom_t;

/* Indexed IMU_A=0, IMU_B=1, IMU_C=2 to match imu_spi.h. */
extern const imu_geom_t imu_geom[IMU_COUNT_GEOM];
