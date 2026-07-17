#pragma once

/*
 * RSSI heading estimation pipeline.
 *
 * Combines interpolation, autocorrelation-based period acquisition,
 * and edge-triggered PLL into a single self-contained estimator.
 * Call push() from the ESP-NOW UART receive path; call estimate()
 * each control tick to get the current heading if locked.
 *
 * Algorithm based on Trevor Gower's rotation_sensing project:
 *   https://github.com/TGower/rotation_sensing
 * Original concept: use ESP-NOW RSSI variation from antenna rotation
 * as a heading sensor for meltybrain combat robots. Autocorrelation
 * finds the rotation period; edge-triggered PLL tracks phase.
 *
 * All state is in the struct. No globals, no allocation after init.
 */

#include <stdint.h>
#include <stdbool.h>
#include "rssi_interp.h"
#include "edge_pll.h"

/* Autocorrelation buffer lives here (not on stack) to avoid
 * blowing the RP2350 4KB core stack. */
#define RSSI_HEADING_BUF_SIZE  RSSI_RING_SIZE

typedef struct {
    /* Sub-components. */
    rssi_interp_t interp;
    edge_pll_t    pll;

    /* Autocorrelation snapshot buffer (avoids stack allocation). */
    float acorr_buf[RSSI_HEADING_BUF_SIZE];

    /* State. */
    bool     pll_initialized;
    uint32_t sample_idx;
    uint32_t autocorr_counter;

    /* Tunables (set at init, adjustable at runtime). */
    uint32_t interval_us;          /* interpolation interval */
    uint32_t autocorr_interval;    /* samples between autocorr runs */
    uint32_t autocorr_min_lag;
    uint32_t autocorr_max_lag;
    float    trigger_thresh;       /* DC-removed RSSI edge threshold */
    float    arm_thresh;           /* re-arm threshold */
    float    min_gap_frac;         /* min inter-edge gap as fraction of period */
    float    pll_kp;
    float    pll_ki;
} rssi_heading_t;

/* Heading estimate output. */
typedef struct {
    float theta;     /* heading [0, 2π), valid only when locked */
    float omega;     /* rotation rate (samples/sample, ≈1.0 when locked) */
    bool  locked;
} rssi_estimate_t;

void rssi_heading_init(rssi_heading_t *rh);

/* Feed a raw RSSI sample with microsecond timestamp. */
void rssi_heading_push(rssi_heading_t *rh, int8_t rssi, int64_t ts_us);

/* Get current heading estimate. Returns locked=false if not ready. */
rssi_estimate_t rssi_heading_estimate(const rssi_heading_t *rh);
