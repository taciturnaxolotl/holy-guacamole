#include "meas_model.h"
#include "imu_geom.h"

#include <math.h>

void meas_predict(const mat_t *x, mat_t *z) {
    float omega = mat_get(x, ST_OMEGA, 0);
    float alpha = mat_get(x, ST_ALPHA, 0);
    float w2 = omega * omega;

    mat_zero(z, MEAS_DIM, 1);

    float ra = imu_geom[0].radius_m;
    float rb = imu_geom[1].radius_m;
    float rc = imu_geom[2].radius_m;

    mat_set(z, MEAS_A_RADIAL,     0, w2 * ra);
    mat_set(z, MEAS_A_TANGENTIAL, 0, alpha * ra);
    mat_set(z, MEAS_A_GYRO,       0, omega);
    mat_set(z, MEAS_B_RADIAL,     0, w2 * rb);
    mat_set(z, MEAS_B_TANGENTIAL, 0, alpha * rb);
    mat_set(z, MEAS_C_RADIAL,     0, w2 * rc);
    mat_set(z, MEAS_C_TANGENTIAL, 0, alpha * rc);
}

void meas_jacobian(const mat_t *x, mat_t *H) {
    float omega = mat_get(x, ST_OMEGA, 0);

    mat_zero(H, MEAS_DIM, ST_DIM);

    float ra = imu_geom[0].radius_m;
    float rb = imu_geom[1].radius_m;
    float rc = imu_geom[2].radius_m;

    /* d(w^2 r)/dw = 2 w r ; d(alpha r)/dalpha = r ; d(gyro)/dw = 1.
     * theta column is all zero (heading is unobservable here). */
    mat_set(H, MEAS_A_RADIAL,     ST_OMEGA, 2.0f * omega * ra);
    mat_set(H, MEAS_A_TANGENTIAL, ST_ALPHA, ra);
    mat_set(H, MEAS_A_GYRO,       ST_OMEGA, 1.0f);
    mat_set(H, MEAS_B_RADIAL,     ST_OMEGA, 2.0f * omega * rb);
    mat_set(H, MEAS_B_TANGENTIAL, ST_ALPHA, rb);
    mat_set(H, MEAS_C_RADIAL,     ST_OMEGA, 2.0f * omega * rc);
    mat_set(H, MEAS_C_TANGENTIAL, ST_ALPHA, rc);
}

void meas_saturation_flags(const mat_t *z, bool saturated[MEAS_DIM]) {
    for (int i = 0; i < MEAS_DIM; i++) saturated[i] = false;

    /* Flag any sensor channel whose reading is at its rail (detected from
     * the measurement itself, not a predicted state, so it catches
     * saturation regardless of estimator lag). A railed reading is clipped
     * garbage; the EKF inflates its noise to ignore it and lean on the
     * remaining sensors. Inner IMU-A accel is +/-320g; outer H3LIS are
     * +/-400g; the inner gyro rails at +/-4000 dps and is pinned during
     * any combat spin, so it MUST be dropped above ~670 rpm or it drags
     * omega toward its clamped value. */
    const float inner = SATURATION_FRAC * LSM6_FULL_SCALE_MS2;
    const float outer = SATURATION_FRAC * H3LIS_FULL_SCALE_MS2;
    const float gyro  = SATURATION_FRAC * GYRO_FULL_SCALE_RADS;

    if (fabsf(mat_get(z, MEAS_A_RADIAL, 0))     >= inner) saturated[MEAS_A_RADIAL] = true;
    if (fabsf(mat_get(z, MEAS_A_TANGENTIAL, 0)) >= inner) saturated[MEAS_A_TANGENTIAL] = true;
    if (fabsf(mat_get(z, MEAS_A_GYRO, 0))       >= gyro)  saturated[MEAS_A_GYRO] = true;
    if (fabsf(mat_get(z, MEAS_B_RADIAL, 0))     >= outer) saturated[MEAS_B_RADIAL] = true;
    if (fabsf(mat_get(z, MEAS_B_TANGENTIAL, 0)) >= outer) saturated[MEAS_B_TANGENTIAL] = true;
    if (fabsf(mat_get(z, MEAS_C_RADIAL, 0))     >= outer) saturated[MEAS_C_RADIAL] = true;
    if (fabsf(mat_get(z, MEAS_C_TANGENTIAL, 0)) >= outer) saturated[MEAS_C_TANGENTIAL] = true;
}
