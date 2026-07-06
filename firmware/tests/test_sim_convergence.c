#include "test_assert.h"
#include "estimation/ekf.h"
#include "estimation/meas_model.h"
#include "robot_sim.h"

#include <math.h>

#define DT 0.001f  /* 1 kHz */
#define RPM_TO_RADS (2.0f * (float)M_PI / 60.0f)

/* Run the sim + EKF together for n_steps at steady omega and report the
 * worst-case omega error and heading error against truth. */
static void run_steady(float rpm, int n_steps, float *max_omega_err,
                       float *max_heading_err) {
    robot_sim_t sim;
    sim_init(&sim, rpm * RPM_TO_RADS, 0xC0FFEEULL);

    ekf_t ekf;
    ekf_init(&ekf, 0.0f);  /* filter starts ignorant of omega */

    *max_omega_err = 0.0f;
    *max_heading_err = 0.0f;

    for (int i = 0; i < n_steps; i++) {
        sim_step(&sim, 0.0, DT);
        mat_t z;
        sim_read(&sim, &z);
        ekf_predict(&ekf, DT);
        ekf_update(&ekf, &z);

        /* Let the filter settle before scoring. */
        if (i < n_steps / 2) continue;

        float we = fabsf(ekf_omega(&ekf) - (float)sim.omega);
        if (we > *max_omega_err) *max_omega_err = we;

        /* Heading error, wrapped to [-pi, pi]. */
        float he = ekf_theta(&ekf) - (float)sim.theta;
        while (he > (float)M_PI) he -= 2.0f * (float)M_PI;
        while (he < -(float)M_PI) he += 2.0f * (float)M_PI;
        he = fabsf(he);
        if (he > *max_heading_err) *max_heading_err = he;
    }
}

/* Tracking mode: 3000 RPM, outer sensors well within range. */
static void test_steady_3000rpm(void) {
    float we, he;
    run_steady(3000.0f, 3000, &we, &he);
    /* omega ~314 rad/s; expect estimate within ~1.5%. */
    ASSERT_TRUE(we < 0.015f * 3000.0f * RPM_TO_RADS);
    /* heading drift bounded over the scored window (~30 deg). */
    ASSERT_TRUE(he < 0.52f);
}

/* Strike mode: 4500 RPM, outer H3LIS radial channels saturate. The
 * filter must keep tracking omega via the inner gyro + inner accel. */
static void test_steady_4500rpm_saturated(void) {
    float we, he;
    run_steady(4500.0f, 3000, &we, &he);
    /* Even with outer radial railed, gyro anchors omega within ~3%. */
    ASSERT_TRUE(we < 0.03f * 4500.0f * RPM_TO_RADS);
    ASSERT_TRUE(he < 0.7f);
}

/* Spinup ramp: accelerate from rest, then hold. Filter should catch up. */
static void test_spinup(void) {
    robot_sim_t sim;
    sim_init(&sim, 0.0, 0x1234ULL);
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);

    float target = 3000.0f * RPM_TO_RADS;
    float alpha = target / 1.0f;  /* reach target in ~1s */

    for (int i = 0; i < 3000; i++) {
        float a = ((float)sim.omega < target) ? alpha : 0.0f;
        sim_step(&sim, a, DT);
        mat_t z;
        sim_read(&sim, &z);
        ekf_predict(&ekf, DT);
        ekf_update(&ekf, &z);
    }

    float we = fabsf(ekf_omega(&ekf) - (float)sim.omega);
    ASSERT_TRUE(we < 0.03f * target);
}

/* Long run must not diverge or produce NaN. */
static void test_long_run_stable(void) {
    robot_sim_t sim;
    sim_init(&sim, 3000.0f * RPM_TO_RADS, 0x55AAULL);
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);

    for (int i = 0; i < 60000; i++) {  /* 60 s at 1 kHz */
        sim_step(&sim, 0.0, DT);
        mat_t z;
        sim_read(&sim, &z);
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
