#include "accel_cal.h"
#include "meas_model.h"
#include "imu_geom.h"

#include <math.h>

/* One (raw_g, factor) table per IMU. */
static float cal_table[ACCEL_CAL_IMUS][ACCEL_CAL_MAX_POINTS * 2];
static int   cal_count[ACCEL_CAL_IMUS];

void accel_cal_init(void) {
    for (int i = 0; i < ACCEL_CAL_IMUS; i++) cal_count[i] = 0;
}

bool accel_cal_add(int imu, float raw_g, float correction_factor) {
    if (imu < 0 || imu >= ACCEL_CAL_IMUS) return false;
    if (cal_count[imu] >= ACCEL_CAL_MAX_POINTS) return false;

    float *t = cal_table[imu];
    int pos = cal_count[imu];
    while (pos > 0 && raw_g < t[(pos - 1) * 2]) {
        t[pos * 2]     = t[(pos - 1) * 2];
        t[pos * 2 + 1] = t[(pos - 1) * 2 + 1];
        pos--;
    }
    t[pos * 2]     = raw_g;
    t[pos * 2 + 1] = correction_factor;
    cal_count[imu]++;
    return true;
}

float accel_cal_get(int imu, float raw_g) {
    if (imu < 0 || imu >= ACCEL_CAL_IMUS) return 1.0f;
    int n = cal_count[imu];
    if (n == 0) return 1.0f;

    const float *t = cal_table[imu];
    if (raw_g <= t[0]) return t[1];                       /* below range */
    if (raw_g >= t[(n - 1) * 2]) return t[(n - 1) * 2 + 1]; /* above range */

    for (int i = 1; i < n; i++) {
        float g0 = t[(i - 1) * 2];
        float g1 = t[i * 2];
        if (raw_g <= g1) {
            float u = (raw_g - g0) / (g1 - g0);
            float f0 = t[(i - 1) * 2 + 1];
            float f1 = t[i * 2 + 1];
            return f0 + u * (f1 - f0);
        }
    }
    return 1.0f;  /* unreachable */
}

int accel_cal_count(int imu) {
    if (imu < 0 || imu >= ACCEL_CAL_IMUS) return 0;
    return cal_count[imu];
}

void accel_cal_apply(mat_t *z) {
    /* Each IMU's accel channels, corrected by that IMU's own curve.
     * corrected = raw * factor(|g|), sign preserved. */
    struct { int imu; int row; } chans[6] = {
        { ACCEL_CAL_IMU_A, MEAS_A_RADIAL },
        { ACCEL_CAL_IMU_A, MEAS_A_TANGENTIAL },
        { ACCEL_CAL_IMU_B, MEAS_B_RADIAL },
        { ACCEL_CAL_IMU_B, MEAS_B_TANGENTIAL },
        { ACCEL_CAL_IMU_C, MEAS_C_RADIAL },
        { ACCEL_CAL_IMU_C, MEAS_C_TANGENTIAL },
    };
    for (int i = 0; i < 6; i++) {
        if (cal_count[chans[i].imu] == 0) continue;
        float v = mat_get(z, chans[i].row, 0);
        float g = fabsf(v) / G_TO_MS2;
        mat_set(z, chans[i].row, 0, v * accel_cal_get(chans[i].imu, g));
    }
}

void accel_cal_clear(void) {
    for (int i = 0; i < ACCEL_CAL_IMUS; i++) cal_count[i] = 0;
}
