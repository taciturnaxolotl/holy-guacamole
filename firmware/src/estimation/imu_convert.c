#include "imu_convert.h"
#include "imu_geom.h"
#include "meas_model.h"

/* Datasheet-nominal sensitivities. CALIBRATE ON BENCH before trusting.
 *
 * H3LIS331DL (outer, IMU-B/C) at +/-400 g: 195 mg/digit in "12-bit
 * representation" (ST DS9012 Rev 5, table 2). The 12 bits are
 * left-justified in the 16-bit output word, so one int16 count is
 * 195/16 = 12.1875 mg, the factor ST's own driver uses
 * (h3lis331dl_from_fs400_to_mg in h3lis331dl_reg.c).
 *
 * LSM6DSV320X (inner, IMU-A): high-g channel at +/-320 g is
 * 10.417 mg/LSB and the gyro at +/-4000 dps is 140 mdps/LSB (ST DS14623
 * Rev 3, table 3). Neither equals range/32768: the int16 rails sit past
 * the rated range (about 341 g and 4587 dps).
 */
#define H3LIS_G_PER_LSB       (0.195f / 16.0f)
#define LSM6_HG_G_PER_LSB     0.010417f
#define LSM6_GYRO_DPS_PER_LSB 0.140f

#define DEG_TO_RAD (0.017453292519943295f)

enum { AXIS_X = 0, AXIS_Y = 1 };

/* Which raw accelerometer axis, with which sign, gives each EKF row.
 *
 * Signs follow what the estimator expects, not where the axis points:
 *   radial     = +omega^2 * r. An accelerometer reports the centripetal
 *                acceleration, which points at the spin centre, so an
 *                axis pointing outward reads negative and gets sign -1.
 *   tangential = +alpha * r along the direction of counter-clockwise
 *                rotation seen from the component side, the same sense
 *                in which gyro Z counts positive.
 *
 * Chip axis directions as mounted (bearing of the axis on the board,
 * chip position bearing in brackets). Derived from the footprint
 * rotations in guac.kicad_pcb (166, 166, 196 degrees) and the axis
 * drawings in the datasheets (DS14623 figure 5, DS9012 figure 2):
 *   U4 [166]: +X at 166 (outward),  +Y at 256 (CCW)
 *   U5 [256]: +X at  76 (inward),   +Y at 166 (CW)
 *   U6 [ 16]: +X at 106 (CCW),      +Y at 196 (inward)
 * docs/spec.md gives +Y / -X as the outward axes of U5 / U6; that only
 * holds if the H3LIS331DL axes lay along its footprint the way the
 * LSM6DSV320X ones do, and DS9012 figure 2 has them a quarter turn off.
 * NOT YET CONFIRMED ON HARDWARE: check with a bench spin (all three
 * radial rows positive and tracking omega^2 * r, tangential near zero
 * at constant speed) and fix this table if a row is wrong.
 */
typedef struct {
    uint8_t radial_axis;
    int8_t  radial_sign;
    uint8_t tangential_axis;
    int8_t  tangential_sign;
} imu_axis_map_t;

static const imu_axis_map_t imu_axis_map[IMU_COUNT] = {
    [IMU_A] = { AXIS_X, -1, AXIS_Y, +1 },
    [IMU_B] = { AXIS_X, +1, AXIS_Y, -1 },
    [IMU_C] = { AXIS_Y, +1, AXIS_X, +1 },
};

static float accel_axis(const imu_sample_t *s, uint8_t axis) {
    return (float)(axis == AXIS_X ? s->accel_x : s->accel_y);
}

static void set_accel_rows(mat_t *z, const imu_sample_t samples[IMU_COUNT],
                           int imu, float g_per_lsb,
                           int radial_row, int tangential_row) {
    const imu_axis_map_t *m = &imu_axis_map[imu];
    float scale = g_per_lsb * G_TO_MS2;
    mat_set(z, radial_row, 0,
            (float)m->radial_sign * accel_axis(&samples[imu], m->radial_axis) * scale);
    mat_set(z, tangential_row, 0,
            (float)m->tangential_sign * accel_axis(&samples[imu], m->tangential_axis) * scale);
}

void imu_samples_to_meas(const imu_sample_t samples[IMU_COUNT], mat_t *z) {
    mat_zero(z, MEAS_DIM, 1);

    /* IMU-A: LSM6DSV320X high-g channel, gyro Z = omega. */
    set_accel_rows(z, samples, IMU_A, LSM6_HG_G_PER_LSB,
                   MEAS_A_RADIAL, MEAS_A_TANGENTIAL);
    mat_set(z, MEAS_A_GYRO, 0,
            samples[IMU_A].gyro_z * LSM6_GYRO_DPS_PER_LSB * DEG_TO_RAD);

    /* IMU-B, IMU-C: H3LIS331DL. */
    set_accel_rows(z, samples, IMU_B, H3LIS_G_PER_LSB,
                   MEAS_B_RADIAL, MEAS_B_TANGENTIAL);
    set_accel_rows(z, samples, IMU_C, H3LIS_G_PER_LSB,
                   MEAS_C_RADIAL, MEAS_C_TANGENTIAL);
}
