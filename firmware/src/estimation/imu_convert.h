#pragma once

/*
 * Convert raw IMU sample counts to the SI measurement vector the EKF
 * consumes (m/s^2 for accel axes, rad/s for the gyro).
 *
 * Pure function: no hardware. Shared by the firmware core-0 path.
 *
 * WARNING - the scale factors below are datasheet-nominal. They MUST be
 * verified/trimmed against a known reference during bench calibration
 * (spin at known RPM, compare centrifugal reading to omega^2*r). Do not
 * trust absolute magnitudes until then. Sign/axis mapping also needs a
 * bench check per the spec's axis-orientation open item.
 */

#include "imu/imu_spi.h"
#include "math/linalg.h"

/* Fill z (MEAS_DIM x 1) from the three raw IMU samples. */
void imu_samples_to_meas(const imu_sample_t samples[IMU_COUNT], mat_t *z);
