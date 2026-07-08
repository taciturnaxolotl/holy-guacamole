#include "imu_synth.h"
#include "estimation/imu_geom.h"
#include "estimation/meas_model.h"

#include <math.h>

/* xorshift64* PRNG: deterministic, seedable. */
static uint64_t rng_next(uint64_t *state) {
    uint64_t x = *state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static float rng_uniform(uint64_t *state) {
    return (float)(rng_next(state) >> 40) / (float)(1 << 24);
}

static float rng_gaussian(uint64_t *state) {
    float u1 = rng_uniform(state);
    float u2 = rng_uniform(state);
    if (u1 < 1e-7f) u1 = 1e-7f;
    return sqrtf(-2.0f * logf(u1)) * cosf(2.0f * (float)M_PI * u2);
}

void imu_synth_init(imu_synth_t *s, uint64_t seed) {
    s->rng = seed ? seed : 0x9E3779B97F4A7C15ULL;
    s->accel_noise_sigma = 1.0f;
    s->gyro_noise_sigma = 0.02f;
    s->enable_noise = true;
    s->enable_saturation = true;
}

void imu_synth_read(imu_synth_t *s, float omega, float alpha, mat_t *z) {
    /* Use the canonical forward model so sim and EKF share exactly one
     * measurement prediction. Then corrupt with noise and saturation. */
    mat_t state;
    mat_zero(&state, ST_DIM, 1);
    mat_set(&state, ST_OMEGA, 0, omega);
    mat_set(&state, ST_ALPHA, 0, alpha);
    meas_predict(&state, z);

    float vals[MEAS_DIM];
    for (int i = 0; i < MEAS_DIM; i++) vals[i] = mat_get(z, i, 0);

    if (s->enable_noise) {
        for (int i = 0; i < MEAS_DIM; i++) {
            float sigma = (i == MEAS_A_GYRO) ? s->gyro_noise_sigma
                                             : s->accel_noise_sigma;
            vals[i] += sigma * rng_gaussian(&s->rng);
        }
    }

    if (s->enable_saturation) {
        float inner = SATURATION_FRAC * LSM6_FULL_SCALE_MS2;
        float outer = SATURATION_FRAC * H3LIS_FULL_SCALE_MS2;
        /* Clamp accel channels to their sensor rails. Gyro doesn't rail. */
        float limits[MEAS_DIM] = { inner, inner, 1e9f, outer, outer, outer, outer };
        for (int i = 0; i < MEAS_DIM; i++) {
            if (vals[i] > limits[i]) vals[i] = limits[i];
            if (vals[i] < -limits[i]) vals[i] = -limits[i];
        }
    }

    for (int i = 0; i < MEAS_DIM; i++) mat_set(z, i, 0, vals[i]);
}
