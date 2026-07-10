#include "test_assert.h"
#include "estimation/ekf.h"
#include "estimation/meas_model.h"
#include "robot_sim.h"

#include <math.h>

#define DT 0.001f  /* 1 kHz */
#define RPM_TO_RADS (2.0f * (float)M_PI / 60.0f)

/* Configure a robot_sim with a *calibrated* sensor: full realistic noise,
 * saturation, gyro rail, bias and vibration, but with the H3LIS
 * nonlinearity removed -- on the real robot accel_cal builds a correction
 * curve for it. Uncorrected, that systematic bias walks heading right off
 * (see the dedicated accel_cal scenario); these tests isolate the filter's
 * behaviour against the residual random errors. */
static void sim_init_calibrated(robot_sim_t *sim, uint64_t seed) {
    sim_init(sim, 0.0, seed);
    sim->synth.enable_nonlinearity = false;
}

/* Spin up from rest to target over ~1s so the gyro (which rails at
 * ~4000 dps = 670 rpm) can bootstrap omega's sign in the low-RPM regime
 * before it saturates -- exactly how the real robot starts. Teleporting
 * to combat RPM with the filter ignorant is unphysical: the gyro would
 * already be railed and omega's sign (unobservable from omega^2 alone)
 * could not be established. */
static void spin_up_to(robot_sim_t *sim, ekf_t *ekf, float target_rads) {
    float alpha = target_rads / 1.0f;  /* reach target in ~1s */
    for (int i = 0; i < 1500; i++) {
        float a = ((float)sim->omega < target_rads) ? alpha : 0.0f;
        sim_step(sim, a, DT);
        mat_t z;
        sim_read(sim, &z, DT);
        ekf_predict(ekf, DT);
        ekf_update(ekf, &z);
    }
}

/* Run the sim + EKF at steady omega (after spin-up) and report the
 * worst-case omega error and heading-rate error against truth. */
static void run_steady(float rpm, int n_steps, float *max_omega_err,
                       float *max_heading_err) {
    robot_sim_t sim;
    sim_init_calibrated(&sim, 0xC0FFEEULL);
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);

    spin_up_to(&sim, &ekf, rpm * RPM_TO_RADS);

    *max_omega_err = 0.0f;
    *max_heading_err = 0.0f;

    /* Re-reference heading error to the offset at the start of scoring:
     * absolute heading is not observable (a fixed bias is expected and
     * trimmed on the real robot), so we score heading DRIFT, not offset. */
    float he0 = ekf_theta(&ekf) - (float)sim.theta;

    for (int i = 0; i < n_steps; i++) {
        sim_step(&sim, 0.0, DT);
        mat_t z;
        sim_read(&sim, &z, DT);
        ekf_predict(&ekf, DT);
        ekf_update(&ekf, &z);

        float we = fabsf(ekf_omega(&ekf) - (float)sim.omega);
        if (we > *max_omega_err) *max_omega_err = we;

        float he = (ekf_theta(&ekf) - (float)sim.theta) - he0;
        while (he > (float)M_PI) he -= 2.0f * (float)M_PI;
        while (he < -(float)M_PI) he += 2.0f * (float)M_PI;
        he = fabsf(he);
        if (he > *max_heading_err) *max_heading_err = he;
    }
}

/* Tracking mode: 3000 RPM. The gyro is railed (314 >> 69.8 rad/s), so
 * omega is held by the accelerometer centrifugal channels alone. */
static void test_steady_3000rpm(void) {
    float we, he;
    run_steady(3000.0f, 3000, &we, &he);
    ASSERT_TRUE(we < 0.015f * 3000.0f * RPM_TO_RADS);  /* within ~1.5% */
    ASSERT_TRUE(he < 0.35f);  /* ~20 deg heading drift over 3s (tracking) */
}

/* Strike mode: 4500 RPM. Outer H3LIS radial channels saturate AND the
 * gyro is long railed, so the inner LSM6 accel (271g at 12mm, in-spec)
 * is the sole omega anchor. */
static void test_steady_4500rpm_saturated(void) {
    float we, he;
    run_steady(4500.0f, 3000, &we, &he);
    ASSERT_TRUE(we < 0.02f * 4500.0f * RPM_TO_RADS);  /* within ~2% */
    ASSERT_TRUE(he < 1.1f);  /* ~60 deg over 3s: strike mode accepts drift */
}

/* Spinup ramp: accelerate from rest, then hold. Filter should catch up. */
static void test_spinup(void) {
    robot_sim_t sim;
    sim_init_calibrated(&sim, 0x1234ULL);
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);

    float target = 3000.0f * RPM_TO_RADS;
    float alpha = target / 1.0f;  /* reach target in ~1s */

    for (int i = 0; i < 3000; i++) {
        float a = ((float)sim.omega < target) ? alpha : 0.0f;
        sim_step(&sim, a, DT);
        mat_t z;
        sim_read(&sim, &z, DT);
        ekf_predict(&ekf, DT);
        ekf_update(&ekf, &z);
    }

    float we = fabsf(ekf_omega(&ekf) - (float)sim.omega);
    ASSERT_TRUE(we < 0.04f * target);
}

/* Long run must not diverge or produce NaN. */
static void test_long_run_stable(void) {
    robot_sim_t sim;
    sim_init_calibrated(&sim, 0x55AAULL);
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);
    spin_up_to(&sim, &ekf, 3000.0f * RPM_TO_RADS);

    for (int i = 0; i < 60000; i++) {  /* 60 s at 1 kHz */
        sim_step(&sim, 0.0, DT);
        mat_t z;
        sim_read(&sim, &z, DT);
        ekf_predict(&ekf, DT);
        ekf_update(&ekf, &z);
    }
    ASSERT_TRUE(mat_is_finite(&ekf.P));
    ASSERT_TRUE(mat_is_finite(&ekf.x));
    ASSERT_TRUE(isfinite(ekf_omega(&ekf)));
}

int main(void) {
    RUN_TEST(test_steady_3000rpm);
    RUN_TEST(test_steady_4500rpm_saturated);
    RUN_TEST(test_spinup);
    RUN_TEST(test_long_run_stable);
    return test_report();
}
