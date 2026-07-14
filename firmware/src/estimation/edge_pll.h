#pragma once

/*
 * Edge-triggered PLL for RSSI-based heading estimation.
 *
 * Locks onto the periodic RSSI null produced by antenna rotation.
 * Detects falling edges through a threshold with hysteresis and
 * minimum inter-edge time to reject sub-harmonics. Between edges
 * the NCO free-runs; at each edge the phase error corrects theta
 * and omega via a PI controller.
 *
 * Derived from Trevor Gower's rotation_sensing project:
 *   https://github.com/TGower/rotation_sensing
 */

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    /* Configuration. */
    float nominal_period;       /* expected period in samples */
    float trigger_thresh;       /* DC-removed RSSI: falling through = edge */
    float arm_thresh;           /* DC-removed RSSI: rise above to re-arm */
    int64_t min_gap_us;         /* minimum microseconds between edges */
    float kp;                   /* proportional gain */
    float ki;                   /* integral gain */
    float lock_threshold;       /* absolute |phase error| EMA threshold (samples) */

    /* NCO state. */
    float theta;                /* phase within current period [0, nominal_period) */
    float omega;                /* samples per sample (ideally 1.0 when locked) */
    float integrator;           /* PI I-state */

    /* Edge detection state. */
    float prev_sample;
    bool  has_prev;
    bool  armed;
    int64_t last_edge_ts;       /* microsecond timestamp of last edge */
    float last_edge_theta;
    bool  has_last_edge;

    /* Lock tracking. */
    float lock_ema;             /* EMA of |phase error| in samples */
    bool  locked;
    uint32_t edge_count;
} edge_pll_t;

void edge_pll_init(edge_pll_t *p, float nominal_period,
                   float trigger_thresh, float arm_thresh,
                   int64_t min_gap_us, float kp, float ki);

/* Feed one interpolated RSSI sample with its microsecond timestamp.
 * Returns true if an edge was detected this sample. */
bool edge_pll_update(edge_pll_t *p, float sample, int64_t ts_us);

float edge_pll_theta_rad(const edge_pll_t *p);
float edge_pll_omega(const edge_pll_t *p);
bool  edge_pll_locked(const edge_pll_t *p);
