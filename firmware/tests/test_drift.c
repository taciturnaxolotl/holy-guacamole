#include "test_assert.h"
#include "control/drift.h"

#include <math.h>

#define PI ((float)M_PI)

/* drift_compute uses cos(theta - phi - pi/2).
 * At theta = phi - pi/2: cos(-pi) = -1 -> mod negative -> B > A
 * At theta = phi:        cos(-pi/2) = 0 -> no differential
 * At theta = phi + pi/2: cos(0) = 1   -> mod positive -> A > B */

/* At theta = phi + pi/2, cos is 1: motor A gets max boost, B max cut. */
static void test_peak_differential(void) {
    drift_throttles_t t = drift_compute(0.5f + PI / 2.0f, 0.5f, 0.3f, 0.5f);
    ASSERT_NEAR(t.a, 0.8f, 1e-5f);
    ASSERT_NEAR(t.b, 0.2f, 1e-5f);
}

/* At theta == phi, cos(-pi/2) = 0: both motors at base. */
static void test_quadrature_no_diff(void) {
    drift_throttles_t t = drift_compute(0.5f, 0.5f, 0.3f, 0.5f);
    ASSERT_NEAR(t.a, 0.5f, 1e-5f);
    ASSERT_NEAR(t.b, 0.5f, 1e-5f);
}

/* At theta = phi - pi/2, cos(-pi) = -1: B gets max boost, A max cut. */
static void test_antiphase_flips(void) {
    drift_throttles_t t = drift_compute(0.5f - PI / 2.0f, 0.5f, 0.3f, 0.5f);
    ASSERT_NEAR(t.a, 0.2f, 1e-5f);
    ASSERT_NEAR(t.b, 0.8f, 1e-5f);
}

/* Throttles clamp to [0,1] when base + authority exceeds range. */
static void test_clamp(void) {
    /* Peak positive mod at theta = phi + pi/2 */
    drift_throttles_t t = drift_compute(PI / 2.0f, 0.9f, 0.5f, 0.0f);
    ASSERT_NEAR(t.a, 1.0f, 1e-5f);   /* 0.9 + 0.5 -> clamped 1.0 */
    ASSERT_NEAR(t.b, 0.4f, 1e-5f);   /* 0.9 - 0.5 */
}

/* Zero authority is pure spin: both motors always at base. */
static void test_zero_authority(void) {
    for (float th = 0.0f; th < 2.0f * PI; th += 0.5f) {
        drift_throttles_t t = drift_compute(th, 0.4f, 0.0f, 1.2f);
        ASSERT_NEAR(t.a, 0.4f, 1e-6f);
        ASSERT_NEAR(t.b, 0.4f, 1e-6f);
    }
}

/* Stick maps to direction and scaled authority. */
static void test_stick_direction(void) {
    float a, phi;
    drift_from_stick(1.0f, 0.0f, 0.8f, &a, &phi);
    ASSERT_NEAR(a, 0.8f, 1e-5f);
    ASSERT_NEAR(phi, 0.0f, 1e-5f);

    drift_from_stick(0.0f, 1.0f, 0.8f, &a, &phi);
    ASSERT_NEAR(phi, PI / 2.0f, 1e-5f);

    /* Half-deflection -> half authority. */
    drift_from_stick(0.5f, 0.0f, 0.8f, &a, &phi);
    ASSERT_NEAR(a, 0.4f, 1e-5f);
}

/* Centered stick -> no drift. */
static void test_stick_deadzone(void) {
    float a, phi;
    drift_from_stick(0.0f, 0.0f, 0.8f, &a, &phi);
    ASSERT_NEAR(a, 0.0f, 1e-6f);
    ASSERT_NEAR(phi, 0.0f, 1e-6f);
}

int main(void) {
    RUN_TEST(test_peak_differential);
    RUN_TEST(test_quadrature_no_diff);
    RUN_TEST(test_antiphase_flips);
    RUN_TEST(test_clamp);
    RUN_TEST(test_zero_authority);
    RUN_TEST(test_stick_direction);
    RUN_TEST(test_stick_deadzone);
    return test_report();
}
