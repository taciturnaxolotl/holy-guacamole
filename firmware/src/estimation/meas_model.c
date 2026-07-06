#include "meas_model.h"
#include "imu_geom.h"

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

void meas_saturation_flags(float omega, bool saturated[MEAS_DIM]) {
    float w2 = omega * omega;
    for (int i = 0; i < MEAS_DIM; i++) saturated[i] = false;

    /* Only the outer H3LIS radial axes can rail (inner LSM6DSV320X is
     * +/-320g but at 12mm never reaches it in the operating range;
     * still, flag any radial channel whose predicted centrifugal
     * magnitude exceeds the outer sensor ceiling). */
    if (w2 * imu_geom[1].radius_m >= H3LIS_FULL_SCALE_MS2)
        saturated[MEAS_B_RADIAL] = true;
    if (w2 * imu_geom[2].radius_m >= H3LIS_FULL_SCALE_MS2)
        saturated[MEAS_C_RADIAL] = true;
}
