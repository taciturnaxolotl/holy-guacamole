#include "test_assert.h"
#include "estimation/edge_pll.h"
#include "estimation/rssi_interp.h"
#include "estimation/autocorr.h"
#include "estimation/ekf.h"

#include <math.h>
#include <stdio.h>

/* Generate a synthetic RSSI waveform: sharp null once per period
 * on a flat plateau, similar to real ESP-NOW data. */
static void generate_rssi(float *buf, int n, int period, float dc_offset) {
    for (int i = 0; i < n; i++) {
        int phase = i % period;
        int null_center = period / 4;
        int null_width = period / 10;
        int dist = phase - null_center;
        if (dist < 0) dist = -dist;
        if (dist < null_width) {
            buf[i] = dc_offset - 15.0f * (1.0f - (float)dist / null_width);
        } else {
            buf[i] = dc_offset + 2.0f;
        }
    }
}

static void test_autocorr_finds_period(void) {
    const int period = 317;
    const int n = period * 6;
    float buf[2048];

    generate_rssi(buf, n, period, -47.0f);

    autocorr_result_t res = autocorr_find_period(buf, n, 100, 800);
    ASSERT_TRUE(res.valid);
    ASSERT_TRUE(res.period_samples > 280 && res.period_samples < 350);
    printf("  autocorr period=%u confidence=%.3f\n",
           res.period_samples, res.confidence);
}

static void test_rssi_interp_uniform_grid(void) {
    rssi_interp_t ri;
    rssi_interp_init(&ri, 100);

    int8_t vals[] = {-40, -45, -50, -55, -60, -55, -50, -45, -40};
    int64_t times[] = {0, 120, 250, 340, 480, 610, 720, 850, 990};

    for (int i = 0; i < 9; i++)
        rssi_interp_push(&ri, vals[i], times[i]);

    uint32_t count = rssi_interp_count(&ri);
    ASSERT_TRUE(count > 0);
    printf("  interp produced %u samples from 9 raw\n", count);
}

static void test_edge_pll_locks(void) {
    const int period = 317;
    const int n = period * 10;
    float raw[4096];

    generate_rssi(raw, n, period, -47.0f);

    /* DC remove */
    float mean = 0;
    for (int i = 0; i < n; i++) mean += raw[i];
    mean /= n;
    for (int i = 0; i < n; i++) raw[i] -= mean;

    float dc_min = raw[0], dc_max = raw[0];
    for (int i = 1; i < n; i++) {
        if (raw[i] < dc_min) dc_min = raw[i];
        if (raw[i] > dc_max) dc_max = raw[i];
    }

    edge_pll_t pll;
    int64_t min_gap_us = (int64_t)(period * 0.6f * 100); /* 100µs interval */
    edge_pll_init(&pll, (float)period,
                  dc_min * 0.5f, dc_max * 0.5f,
                  min_gap_us, 0.05f, 0.0005f);

    int lock_count = 0;
    for (int i = 0; i < n; i++) {
        int64_t ts = (int64_t)i * 100; /* 100µs per sample */
        edge_pll_update(&pll, raw[i], ts);
        if (edge_pll_locked(&pll)) lock_count++;
    }

    printf("  edge PLL: %d/%d locked, omega=%.5f, edges=%u\n",
           lock_count, n, edge_pll_omega(&pll), pll.edge_count);
    ASSERT_TRUE(pll.edge_count >= 5);
    ASSERT_TRUE(edge_pll_omega(&pll) > 0.95f && edge_pll_omega(&pll) < 1.05f);
}

static void test_ekf_heading_update(void) {
    ekf_t e;
    ekf_init(&e, 100.0f);

    float theta_before = ekf_theta(&e);
    ekf_update_heading(&e, 1.5f, 0.03f);
    float theta_after = ekf_theta(&e);

    printf("  EKF heading: %.3f -> %.3f (target 1.5)\n",
           theta_before, theta_after);
    ASSERT_TRUE(fabsf(theta_after - 1.5f) < fabsf(theta_before - 1.5f));
}

int main(void) {
    RUN_TEST(test_autocorr_finds_period);
    RUN_TEST(test_rssi_interp_uniform_grid);
    RUN_TEST(test_edge_pll_locks);
    RUN_TEST(test_ekf_heading_update);
    return test_report();
}
