#pragma once

/*
 * Autocorrelation-based period finder for RSSI rotation sensing.
 *
 * Computes the autocorrelation of a DC-removed RSSI buffer and finds
 * the first significant peak, which corresponds to the rotation period.
 * Uses Trevor Gower's valley-detector heuristic on the difference
 * function (SAD) to avoid locking onto harmonics.
 *
 * Based on Trevor Gower's rotation_sensing project:
 *   https://github.com/TGower/rotation_sensing
 *
 * This provides the initial period estimate for edge_pll_init() and
 * can be re-run periodically to track RPM changes or re-acquire after
 * signal loss.
 */

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint32_t period_samples;  /* dominant period in samples */
    float    confidence;      /* autocorrelation peak height [0,1] */
    bool     valid;           /* true if a valid period was found */
} autocorr_result_t;

/* Find the dominant period in buf[0..n-1] via autocorrelation.
 * Searches lags in [min_lag, max_lag]. Returns result with valid=false
 * if no significant peak is found. */
autocorr_result_t autocorr_find_period(const float *buf, uint32_t n,
                                       uint32_t min_lag, uint32_t max_lag);
