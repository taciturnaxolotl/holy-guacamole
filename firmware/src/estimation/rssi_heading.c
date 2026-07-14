#include "rssi_heading.h"
#include "autocorr.h"

#include <string.h>

/* Defaults tuned against real ESP-NOW dump data. */
#define DEFAULT_INTERVAL_US       100
#define DEFAULT_AUTOCORR_INTERVAL 5000
#define DEFAULT_AUTOCORR_MIN_LAG  100
#define DEFAULT_AUTOCORR_MAX_LAG  800
#define DEFAULT_TRIGGER_THRESH    -5.0f
#define DEFAULT_ARM_THRESH         2.0f
#define DEFAULT_MIN_GAP_FRAC       0.6f
#define DEFAULT_PLL_KP             0.05f
#define DEFAULT_PLL_KI             0.0005f

void rssi_heading_init(rssi_heading_t *rh) {
    memset(rh, 0, sizeof(*rh));

    rh->interval_us = DEFAULT_INTERVAL_US;
    rh->autocorr_interval = DEFAULT_AUTOCORR_INTERVAL;
    rh->autocorr_min_lag = DEFAULT_AUTOCORR_MIN_LAG;
    rh->autocorr_max_lag = DEFAULT_AUTOCORR_MAX_LAG;
    rh->trigger_thresh = DEFAULT_TRIGGER_THRESH;
    rh->arm_thresh = DEFAULT_ARM_THRESH;
    rh->min_gap_frac = DEFAULT_MIN_GAP_FRAC;
    rh->pll_kp = DEFAULT_PLL_KP;
    rh->pll_ki = DEFAULT_PLL_KI;

    rssi_interp_init(&rh->interp, rh->interval_us);
}

void rssi_heading_push(rssi_heading_t *rh, int8_t rssi, int64_t ts_us) {
    uint32_t before = rssi_interp_count(&rh->interp);
    rssi_interp_push(&rh->interp, rssi, ts_us);
    uint32_t after = rssi_interp_count(&rh->interp);

    /* Feed each new interpolated sample to the edge PLL via read_at,
     * which respects the abstraction boundary instead of reaching
     * into ring buffer internals. */
    for (uint32_t i = before; i < after; i++) {
        float sample;
        if (rssi_interp_read_at(&rh->interp, i, &sample))
            edge_pll_update(&rh->pll, sample, ts_us);
    }
    rh->sample_idx = after;

    /* Periodic autocorrelation for acquisition / re-acquisition. */
    rh->autocorr_counter += (after - before);
    if (rh->autocorr_counter >= rh->autocorr_interval) {
        rh->autocorr_counter = 0;

        uint32_t n = after < RSSI_HEADING_BUF_SIZE ? after : RSSI_HEADING_BUF_SIZE;
        if (n >= rh->autocorr_max_lag * 2) {
            /* Read into the struct's buffer, not the stack. */
            uint32_t got = rssi_interp_read_recent(&rh->interp, rh->acorr_buf, n);

            autocorr_result_t ac = autocorr_find_period(
                rh->acorr_buf, got, rh->autocorr_min_lag, rh->autocorr_max_lag);

            if (ac.valid && !rh->pll_initialized) {
                float period = (float)ac.period_samples;
                int64_t min_gap_us = (int64_t)(period * rh->min_gap_frac * rh->interval_us);

                edge_pll_init(&rh->pll, period,
                              rh->trigger_thresh, rh->arm_thresh,
                              min_gap_us, rh->pll_kp, rh->pll_ki);
                rh->pll_initialized = true;
            }
        }
    }
}

rssi_estimate_t rssi_heading_estimate(const rssi_heading_t *rh) {
    rssi_estimate_t est = { .locked = false };

    if (!rh->pll_initialized)
        return est;

    est.locked = edge_pll_locked(&rh->pll);
    if (est.locked) {
        est.theta = edge_pll_theta_rad(&rh->pll);
        est.omega = edge_pll_omega(&rh->pll);
    }

    return est;
}
