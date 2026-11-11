#pragma once

/*
 * Convert raw IMU sample counts to the SI measurement vector the EKF
 * consumes (m/s^2 for accel axes, rad/s for the gyro).
 *
 * Pure function: no hardware. Shared by the firmware core-0 path.
 *
 * WARNING - the scale factors are datasheet-nominal. They MUST be
 * verified/trimmed against a known reference during bench calibration
 * (spin at known RPM, compare centrifugal reading to omega^2*r). Do not
 * trust absolute magnitudes until then.
 *
 * The three chips are mounted in three different orientations, so the
 * conversion goes through a per-chip axis and sign table (in the .c).
 * That table comes from the datasheet axis drawings and the footprint
 * rotations and has not been checked on hardware: it needs the bench
 * spin from the spec's axis-orientation open item.
 */

#include "imu/imu_spi.h"
#include "math/linalg.h"

/* Fill z (MEAS_DIM x 1) from the three raw IMU samples. Radial rows come
 * out as +omega^2 * r and tangential rows as +alpha * r (counter-clockwise
 * positive seen from the component side), matching meas_predict(). */
void imu_samples_to_meas(const imu_sample_t samples[IMU_COUNT], mat_t *z);
