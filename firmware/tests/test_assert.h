#pragma once

/*
 * Minimal host test harness. Zero dependencies beyond stdio.
 * Each test file defines tests and calls these macros; a test
 * "passes" if it reaches the end without a failed assertion.
 *
 * Usage:
 *   #include "test_assert.h"
 *   static void test_thing(void) {
 *       ASSERT_TRUE(1 + 1 == 2);
 *       ASSERT_NEAR(3.14f, 3.15f, 0.02f);
 *   }
 *   int main(void) {
 *       RUN_TEST(test_thing);
 *       return test_report();
 *   }
 */

#include <stdio.h>
#include <math.h>

static int t_tests_run = 0;
static int t_tests_failed = 0;
static int t_current_failed = 0;

#define ASSERT_TRUE(cond)                                                     \
    do {                                                                      \
        if (!(cond)) {                                                        \
            printf("    FAIL %s:%d: ASSERT_TRUE(%s)\n", __FILE__, __LINE__,   \
                   #cond);                                                    \
            t_current_failed = 1;                                             \
        }                                                                     \
    } while (0)

#define ASSERT_NEAR(got, want, tol)                                           \
    do {                                                                      \
        float _g = (got), _w = (want), _t = (tol);                            \
        if (!(fabsf(_g - _w) <= _t)) {                                        \
            printf("    FAIL %s:%d: %s=%.6g not within %.6g of %.6g\n",       \
                   __FILE__, __LINE__, #got, (double)_g, (double)_t,          \
                   (double)_w);                                               \
            t_current_failed = 1;                                             \
        }                                                                     \
    } while (0)

#define RUN_TEST(fn)                                                          \
    do {                                                                      \
        t_current_failed = 0;                                                 \
        t_tests_run++;                                                        \
        fn();                                                                 \
        if (t_current_failed) {                                               \
            t_tests_failed++;                                                 \
            printf("[FAIL] %s\n", #fn);                                       \
        } else {                                                              \
            printf("[ ok ] %s\n", #fn);                                       \
        }                                                                     \
    } while (0)

static inline int test_report(void) {
    printf("\n%d tests, %d failed\n", t_tests_run, t_tests_failed);
    return t_tests_failed == 0 ? 0 : 1;
}
