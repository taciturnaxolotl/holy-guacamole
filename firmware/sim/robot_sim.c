#include "robot_sim.h"
#include "estimation/imu_geom.h"
#include "estimation/meas_model.h"

#include <math.h>

/* xorshift64* PRNG: deterministic, seedable, good enough for test noise. */
static uint64_t rng_next(uint64_t *state) {
    uint64_t x = *state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static float rng_uniform(uint64_t *state) {
    /* [0,1) from top 24 bits */
    return (float)(rng_next(state) >> 40) / (float)(1 << 24);
}

/* Standard-normal sample via Box-Muller. */
static float rng_gaussian(uint64_t *state) {
    float u1 = rng_uniform(state);
    float u2 = rng_uniform(state);
    if (u1 < 1e-7f) u1 = 1e-7f;  /* avoid log(0) */
    return sqrtf(-2.0f * logf(u1)) * cosf(2.0f * (float)M_PI * u2);
}

void sim_init(robot_sim_t *s, double omega0, uint64_t seed) {
    s->theta = 0.0;
    s->omega = omega0;
    s->alpha = 0.0;
    s->rng = seed ? seed : 0x9E3779B97F4A7C15ULL;
    /* H3LIS331DL accel noise density ~ a few mg/sqrt(Hz); at 1kHz this
     * lands around 0.5-1 m/s^2 RMS. Gyro noise is small. Conservative. */
    s->accel_noise_sigma = 1.0f;
    s->gyro_noise_sigma = 0.02f;
    s->enable_noise = true;
    s->enable_saturation = true;
}

void sim_step(robot_sim_t *s, double alpha_cmd, double dt) {
    s->alpha = alpha_cmd;
    s->theta += s->omega * dt + 0.5 * s->alpha * dt * dt;
    s->omega += s->alpha * dt;
}

void sim_kick_omega(robot_sim_t *s, double domega) {
    s->omega += domega;
}

static float clip(float v, float limit) {
    if (v > limit) return limit;
    if (v < -limit) return -limit;
    return v;
}

void sim_read(robot_sim_t *s, mat_t *z) {
    float omega = (float)s->omega;
    float alpha = (float)s->alpha;
    float w2 = omega * omega;

    mat_zero(z, MEAS_DIM, 1);

    /* Ideal readings from rigid-body kinematics. */
    float ra = imu_geom[0].radius_m;
    float rb = imu_geom[1].radius_m;
    float rc = imu_geom[2].radius_m;

    float vals[MEAS_DIM];
    vals[MEAS_A_RADIAL]     = w2 * ra;
    vals[MEAS_A_TANGENTIAL] = alpha * ra;
    vals[MEAS_A_GYRO]       = omega;
    vals[MEAS_B_RADIAL]     = w2 * rb;
    vals[MEAS_B_TANGENTIAL] = alpha * rb;
    vals[MEAS_C_RADIAL]     = w2 * rc;
    vals[MEAS_C_TANGENTIAL] = alpha * rc;

    /* Additive Gaussian noise. */
    if (s->enable_noise) {
        for (int i = 0; i < MEAS_DIM; i++) {
            float sigma = (i == MEAS_A_GYRO) ? s->gyro_noise_sigma
                                             : s->accel_noise_sigma;
            vals[i] += sigma * rng_gaussian(&s->rng);
        }
    }

    /* Sensor saturation: outer H3LIS accel axes clip at +/-400g;
     * inner LSM6DSV320X accel clips at +/-320g. Gyro doesn't rail here. */
    if (s->enable_saturation) {
        float outer = H3LIS_FULL_SCALE_MS2;
        float inner = 320.0f * G_TO_MS2;
        vals[MEAS_A_RADIAL]     = clip(vals[MEAS_A_RADIAL], inner);
        vals[MEAS_A_TANGENTIAL] = clip(vals[MEAS_A_TANGENTIAL], inner);
        vals[MEAS_B_RADIAL]     = clip(vals[MEAS_B_RADIAL], outer);
        vals[MEAS_B_TANGENTIAL] = clip(vals[MEAS_B_TANGENTIAL], outer);
        vals[MEAS_C_RADIAL]     = clip(vals[MEAS_C_RADIAL], outer);
        vals[MEAS_C_TANGENTIAL] = clip(vals[MEAS_C_TANGENTIAL], outer);
    }

    for (int i = 0; i < MEAS_DIM; i++) mat_set(z, i, 0, vals[i]);
}
