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

    /* Datasheet-anchored white noise: the outer H3LIS are markedly noisier
     * than the inner LSM6 high-g, and the gyro is very quiet. */
    s->accel_inner_sigma = 0.30f;   /* m/s^2 (LSM6 ~1.5 mg/rtHz) */
    s->accel_outer_sigma = 2.50f;   /* m/s^2 (H3LIS ~15 mg/rtHz) */
    s->gyro_sigma        = 0.0015f; /* rad/s (LSM6 ~3.8 mdps/rtHz) */

    /* Quantization LSB at the operating full-scale ranges. */
    s->accel_inner_lsb = 0.0958f;   /* 9.77 mg at +/-320g */
    s->accel_outer_lsb = 1.912f;    /* 195 mg at +/-400g */
    s->gyro_lsb        = 0.00244f;  /* 140 mdps at +/-4000 dps */

    /* Gyro bias: a fixed offset drawn once (~0.5 deg/s) plus a slow
     * in-run random walk. */
    s->gyro_bias      = 0.0087f * rng_gaussian(&s->rng);
    s->gyro_bias_walk = 0.002f;     /* rad/s per sqrt(s) */

    s->outer_nonlinearity = 0.05f;  /* 5% droop at full scale (H3LIS) */
    s->vibration          = 3.0f;   /* m/s^2 spin-synchronous */
    s->vib_phase          = 0.0f;

    s->enable_noise        = true;
    s->enable_saturation   = true;
    s->enable_bias         = true;
    s->enable_nonlinearity = true;
    s->enable_vibration    = true;
    s->enable_quant        = true;
}

/* Which measurement rows are outer (H3LIS) accelerometer channels. */
static bool is_outer_accel(int row) {
    return row == MEAS_B_RADIAL || row == MEAS_B_TANGENTIAL ||
           row == MEAS_C_RADIAL || row == MEAS_C_TANGENTIAL;
}

static float quantize(float v, float lsb) {
    if (lsb <= 0.0f) return v;
    return lsb * floorf(v / lsb + 0.5f);
}

void imu_synth_read(imu_synth_t *s, float omega, float alpha, float dt, mat_t *z) {
    /* Use the canonical forward model so sim and EKF share exactly one
     * measurement prediction. Then corrupt with the sensor imperfections
     * the EKF does NOT model. */
    mat_t state;
    mat_zero(&state, ST_DIM, 1);
    mat_set(&state, ST_OMEGA, 0, omega);
    mat_set(&state, ST_ALPHA, 0, alpha);
    meas_predict(&state, z);

    /* Advance spin-synchronous vibration phase and gyro bias walk. */
    s->vib_phase += omega * dt;
    if (s->enable_bias)
        s->gyro_bias += s->gyro_bias_walk * sqrtf(dt > 0.0f ? dt : 0.0f) * rng_gaussian(&s->rng);
    float vib = s->enable_vibration
                    ? s->vibration * (sinf(s->vib_phase) + 0.5f * sinf(2.0f * s->vib_phase))
                    : 0.0f;

    float vals[MEAS_DIM];
    for (int i = 0; i < MEAS_DIM; i++) vals[i] = mat_get(z, i, 0);

    for (int i = 0; i < MEAS_DIM; i++) {
        bool is_gyro = (i == MEAS_A_GYRO);
        bool outer = is_outer_accel(i);

        /* H3LIS nonlinearity: sensor under-reads toward its rail. This is
         * exactly the deviation accel_cal builds a correction curve for. */
        if (s->enable_nonlinearity && outer) {
            float frac = vals[i] / H3LIS_FULL_SCALE_MS2;
            vals[i] *= (1.0f - s->outer_nonlinearity * frac * frac);
        }

        /* Spin-synchronous vibration on accel channels only. */
        if (!is_gyro) vals[i] += vib;

        /* Gyro bias. */
        if (is_gyro && s->enable_bias) vals[i] += s->gyro_bias;

        /* White noise, per sensor family. */
        if (s->enable_noise) {
            float sigma = is_gyro ? s->gyro_sigma
                        : outer   ? s->accel_outer_sigma
                                  : s->accel_inner_sigma;
            vals[i] += sigma * rng_gaussian(&s->rng);
        }

        /* Hard rails: accel full-scale, gyro +/-4000 dps. */
        if (s->enable_saturation) {
            float limit = is_gyro ? GYRO_FULL_SCALE_RADS
                        : outer   ? H3LIS_FULL_SCALE_MS2
                                  : LSM6_FULL_SCALE_MS2;
            if (vals[i] >  limit) vals[i] =  limit;
            if (vals[i] < -limit) vals[i] = -limit;
        }

        /* Quantization to the sensor LSB. */
        if (s->enable_quant) {
            float lsb = is_gyro ? s->gyro_lsb
                      : outer   ? s->accel_outer_lsb
                                : s->accel_inner_lsb;
            vals[i] = quantize(vals[i], lsb);
        }
    }

    for (int i = 0; i < MEAS_DIM; i++) mat_set(z, i, 0, vals[i]);
}
