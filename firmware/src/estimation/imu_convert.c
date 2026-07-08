#include "imu_convert.h"
#include "imu_geom.h"
#include "meas_model.h"

/* Datasheet-nominal scale factors. CALIBRATE ON BENCH before trusting.
 *
 * H3LIS331DL (outer, IMU-B/C): +/-400g full scale, 12-bit left-justified
 * in a 16-bit register -> ~0.195 g per 12-bit count = 0.195/16 g per
 * int16 count.
 *
 * LSM6DSV320X (inner, IMU-A): +/-320g accel and +/-4000 dps gyro over
 * the full int16 range.
 */
#define H3LIS_G_PER_LSB      (0.195f / 16.0f)
#define LSM6_ACCEL_G_PER_LSB (320.0f / 32768.0f)
#define LSM6_GYRO_DPS_PER_LSB (4000.0f / 32768.0f)

#define DEG_TO_RAD (0.017453292519943295f)

void imu_samples_to_meas(const imu_sample_t samples[IMU_COUNT], mat_t *z) {
    mat_zero(z, MEAS_DIM, 1);

    /* IMU-A: LSM6DSV320X. X=radial, Y=tangential, gyro Z = omega. */
    mat_set(z, MEAS_A_RADIAL, 0,
            samples[IMU_A].accel_x * LSM6_ACCEL_G_PER_LSB * G_TO_MS2);
    mat_set(z, MEAS_A_TANGENTIAL, 0,
            samples[IMU_A].accel_y * LSM6_ACCEL_G_PER_LSB * G_TO_MS2);
    mat_set(z, MEAS_A_GYRO, 0,
            samples[IMU_A].gyro_z * LSM6_GYRO_DPS_PER_LSB * DEG_TO_RAD);

    /* IMU-B: H3LIS331DL. */
    mat_set(z, MEAS_B_RADIAL, 0,
            samples[IMU_B].accel_x * H3LIS_G_PER_LSB * G_TO_MS2);
    mat_set(z, MEAS_B_TANGENTIAL, 0,
            samples[IMU_B].accel_y * H3LIS_G_PER_LSB * G_TO_MS2);

    /* IMU-C: H3LIS331DL. */
    mat_set(z, MEAS_C_RADIAL, 0,
            samples[IMU_C].accel_x * H3LIS_G_PER_LSB * G_TO_MS2);
    mat_set(z, MEAS_C_TANGENTIAL, 0,
            samples[IMU_C].accel_y * H3LIS_G_PER_LSB * G_TO_MS2);
}
