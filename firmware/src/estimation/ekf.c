#include "ekf.h"
#include "imu_geom.h"

#include <math.h>

void ekf_init(ekf_t *e, float omega0) {
    mat_zero(&e->x, ST_DIM, 1);
    mat_set(&e->x, ST_OMEGA, 0, omega0);

    /* Large initial uncertainty: we don't trust the starting guess. */
    mat_identity(&e->P, ST_DIM);
    mat_set(&e->P, ST_THETA, ST_THETA, 100.0f);
    mat_set(&e->P, ST_OMEGA, ST_OMEGA, 100.0f);
    mat_set(&e->P, ST_ALPHA, ST_ALPHA, 100.0f);

    /* Defaults; tune against the simulator and later real logs.
     * r_gyro/r_accel are variances matched to expected sensor noise:
     * an over-large r_gyro makes omega lag during spin-up (heading
     * offset), so it tracks the gyro's true ~0.02 rad/s sigma. */
    e->q_theta = 1e-5f;
    e->q_omega = 20.0f;   /* omega changes fast under motor torque/impact */
    e->q_alpha = 2.0f;
    e->r_accel = 1.0f;    /* (m/s^2)^2 */
    e->r_gyro  = 0.00001f; /* (rad/s)^2, matches ~0.02 rad/s sigma */
    /* Saturation inflation must be large enough to truly drop a railed
     * channel. r_gyro is tiny (1e-5), so a modest factor leaves the railed
     * gyro (pinned at +/-4000 dps) still tugging omega below its true value
     * by ~0.2 rad/s at combat RPM -- a constant bias that dead-reckons into
     * rapid heading drift. 1e10 makes the effective sigma huge (~1e5) so the
     * railed reading contributes nothing. */
    e->sat_inflation = 1e10f;
}

void ekf_predict(ekf_t *e, float dt) {
    float theta = mat_get(&e->x, ST_THETA, 0);
    float omega = mat_get(&e->x, ST_OMEGA, 0);
    float alpha = mat_get(&e->x, ST_ALPHA, 0);

    /* Rate-limit alpha to reject gyro spikes from wall impacts.
     * Derivation: max motor torque produces ~300 rad/s^2 during spin-up.
     * Wall bounces produce 5000+ rad/s^2 transients that are physically
     * impossible from motors alone. 500 rad/s^2 passes all legitimate
     * dynamics while rejecting impact artifacts. */
    const float alpha_max = 500.0f;
    if (alpha > alpha_max) alpha = alpha_max;
    if (alpha < -alpha_max) alpha = -alpha_max;
    mat_set(&e->x, ST_ALPHA, 0, alpha);

    /* State transition (constant-alpha kinematics). Wrap theta into
     * [0, 2*pi) so the stored angle never grows large: at high RPM an
     * unbounded float32 heading loses precision (tens of degrees of
     * phantom drift over a match). theta is decoupled from the
     * measurement model, so wrapping it is exact and side-effect-free. */
    float new_theta = wrap_0_2pi(theta + omega * dt + 0.5f * alpha * dt * dt);
    mat_set(&e->x, ST_THETA, 0, new_theta);
    mat_set(&e->x, ST_OMEGA, 0, omega + alpha * dt);
    /* alpha unchanged */

    /* Jacobian F of the transition. */
    mat_t F;
    mat_identity(&F, ST_DIM);
    mat_set(&F, ST_THETA, ST_OMEGA, dt);
    mat_set(&F, ST_THETA, ST_ALPHA, 0.5f * dt * dt);
    mat_set(&F, ST_OMEGA, ST_ALPHA, dt);

    /* P = F P F^T + Q */
    mat_t FP, FPFt;
    mat_mul(&FP, &F, &e->P);
    mat_mul_transpose(&FPFt, &FP, &F);

    mat_t Q;
    mat_zero(&Q, ST_DIM, ST_DIM);
    mat_set(&Q, ST_THETA, ST_THETA, e->q_theta * dt);
    mat_set(&Q, ST_OMEGA, ST_OMEGA, e->q_omega * dt);
    mat_set(&Q, ST_ALPHA, ST_ALPHA, e->q_alpha * dt);

    mat_add(&e->P, &FPFt, &Q);
    mat_symmetrize(&e->P);
}

void ekf_update(ekf_t *e, const mat_t *z) {
    /* Predicted measurement and Jacobian at the current state. */
    mat_t h, H;
    meas_predict(&e->x, &h);
    meas_jacobian(&e->x, &H);

    /* Innovation y = z - h. */
    mat_t y;
    mat_sub(&y, z, &h);

    /* Measurement noise R (diagonal), with saturation inflation. */
    bool sat[MEAS_DIM];
    meas_saturation_flags(z, sat);

    mat_t R;
    mat_zero(&R, MEAS_DIM, MEAS_DIM);
    for (int i = 0; i < MEAS_DIM; i++) {
        float base = (i == MEAS_A_GYRO) ? e->r_gyro : e->r_accel;
        if (sat[i]) base *= e->sat_inflation;
        mat_set(&R, i, i, base);
    }

    /* S = H P H^T + R */
    mat_t HP, S;
    mat_mul(&HP, &H, &e->P);
    mat_mul_transpose(&S, &HP, &H);
    mat_add(&S, &S, &R);

    /* K = P H^T S^-1 */
    mat_t Sinv;
    if (!mat_invert(&Sinv, &S)) return;  /* skip update if degenerate */

    mat_t Ht, PHt, K;
    mat_transpose(&Ht, &H);
    mat_mul(&PHt, &e->P, &Ht);
    mat_mul(&K, &PHt, &Sinv);

    /* x += K y */
    mat_t Ky;
    mat_mul(&Ky, &K, &y);
    mat_add(&e->x, &e->x, &Ky);

    /* Joseph form: P = (I - KH) P (I - KH)^T + K R K^T
     * Numerically robust; keeps P positive-definite under float32. */
    mat_t KH, ImKH, I;
    mat_mul(&KH, &K, &H);
    mat_identity(&I, ST_DIM);
    mat_sub(&ImKH, &I, &KH);

    mat_t tmp, term1;
    mat_mul(&tmp, &ImKH, &e->P);
    mat_mul_transpose(&term1, &tmp, &ImKH);

    mat_t KR, term2;
    mat_mul(&KR, &K, &R);
    mat_mul_transpose(&term2, &KR, &K);

    mat_add(&e->P, &term1, &term2);
    mat_symmetrize(&e->P);
}

float ekf_theta(const ekf_t *e) { return mat_get(&e->x, ST_THETA, 0); }
float ekf_omega(const ekf_t *e) { return mat_get(&e->x, ST_OMEGA, 0); }
float ekf_alpha(const ekf_t *e) { return mat_get(&e->x, ST_ALPHA, 0); }

float ekf_heading_wrapped(const ekf_t *e) {
    return wrap_0_2pi(ekf_theta(e));
}

void ekf_update_heading(ekf_t *e, float theta_meas, float r_theta) {
    /* Scalar measurement: z = theta_meas, h(x) = x[ST_THETA].
     * H = [1, 0, 0], so this simplifies to a 1D Kalman update
     * on the theta state. We still use Joseph form for robustness. */
    float theta = mat_get(&e->x, ST_THETA, 0);

    /* Innovation with angle wrapping. */
    float y = theta_meas - theta;
    float two_pi = 2.0f * (float)M_PI;
    while (y > (float)M_PI)  y -= two_pi;
    while (y < -(float)M_PI) y += two_pi;

    /* S = P[0,0] + R */
    float p_tt = mat_get(&e->P, ST_THETA, ST_THETA);
    float s = p_tt + r_theta;
    if (s < 1e-12f) return;

    /* K = P[:,0] / S (column vector). */
    float k[ST_DIM];
    for (int i = 0; i < ST_DIM; i++)
        k[i] = mat_get(&e->P, i, ST_THETA) / s;

    /* x += K * y */
    for (int i = 0; i < ST_DIM; i++)
        mat_set(&e->x, i, 0, mat_get(&e->x, i, 0) + k[i] * y);

    /* Wrap theta back into [0, 2*pi). */
    mat_set(&e->x, ST_THETA, 0,
            wrap_0_2pi(mat_get(&e->x, ST_THETA, 0)));

    /* Joseph form: P = (I - KH) P (I - KH)^T + K R K^T
     * With H = [1,0,0], (I-KH) is identity minus first column scaled by k. */
    mat_t ImKH;
    mat_identity(&ImKH, ST_DIM);
    for (int i = 0; i < ST_DIM; i++)
        mat_set(&ImKH, i, ST_THETA,
                mat_get(&ImKH, i, ST_THETA) - k[i]);

    mat_t tmp, term1;
    mat_mul(&tmp, &ImKH, &e->P);
    mat_mul_transpose(&term1, &tmp, &ImKH);

    /* K R K^T */
    mat_t term2;
    mat_zero(&term2, ST_DIM, ST_DIM);
    for (int i = 0; i < ST_DIM; i++)
        for (int j = 0; j < ST_DIM; j++)
            mat_set(&term2, i, j, k[i] * r_theta * k[j]);

    mat_add(&e->P, &term1, &term2);
    mat_symmetrize(&e->P);
}
