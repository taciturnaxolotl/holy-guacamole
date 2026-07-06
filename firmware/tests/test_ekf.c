#include "test_assert.h"
#include "estimation/ekf.h"
#include "estimation/meas_model.h"

/* Predict should advance theta and omega by the kinematic model. */
static void test_predict_kinematics(void) {
    ekf_t e;
    ekf_init(&e, 0.0f);
    mat_set(&e.x, ST_THETA, 0, 0.0f);
    mat_set(&e.x, ST_OMEGA, 0, 10.0f);
    mat_set(&e.x, ST_ALPHA, 0, 2.0f);

    ekf_predict(&e, 0.1f);

    /* theta = 0 + 10*0.1 + 0.5*2*0.01 = 1.01 ; omega = 10 + 2*0.1 = 10.2 */
    ASSERT_NEAR(ekf_theta(&e), 1.01f, 1e-4f);
    ASSERT_NEAR(ekf_omega(&e), 10.2f, 1e-4f);
    ASSERT_NEAR(ekf_alpha(&e), 2.0f, 1e-6f);
}

/* A measurement consistent with a known omega should pull the estimate
 * toward it over repeated updates. */
static void test_update_pulls_omega(void) {
    ekf_t e;
    ekf_init(&e, 0.0f);  /* start believing omega=0 */

    /* Build a measurement for a true omega of 300 rad/s, alpha 0. */
    mat_t truth, z;
    mat_zero(&truth, ST_DIM, 1);
    mat_set(&truth, ST_OMEGA, 0, 300.0f);
    meas_predict(&truth, &z);

    for (int i = 0; i < 50; i++) {
        ekf_predict(&e, 0.001f);
        ekf_update(&e, &z);
    }

    ASSERT_NEAR(ekf_omega(&e), 300.0f, 5.0f);
}

/* Covariance must stay finite and symmetric after many steps. */
static void test_covariance_stays_finite(void) {
    ekf_t e;
    ekf_init(&e, 100.0f);
    mat_t z;
    mat_t truth;
    mat_zero(&truth, ST_DIM, 1);
    mat_set(&truth, ST_OMEGA, 0, 100.0f);
    meas_predict(&truth, &z);

    for (int i = 0; i < 5000; i++) {
        ekf_predict(&e, 0.001f);
        ekf_update(&e, &z);
    }
    ASSERT_TRUE(mat_is_finite(&e.P));
    /* symmetry */
    ASSERT_NEAR(mat_get(&e.P, 0, 1), mat_get(&e.P, 1, 0), 1e-4f);
    ASSERT_NEAR(mat_get(&e.P, 1, 2), mat_get(&e.P, 2, 1), 1e-4f);
}

int main(void) {
    RUN_TEST(test_predict_kinematics);
    RUN_TEST(test_update_pulls_omega);
    RUN_TEST(test_covariance_stays_finite);
    return test_report();
}
