#include "edge_pll.h"

#include <math.h>
#include <string.h>

/* EMA smoothing factor for lock metric. */
#define LOCK_EMA_ALPHA 0.3f

/* Anti-windup clamp on integrator. */
#define INTEGRATOR_CLAMP 0.1f

void edge_pll_init(edge_pll_t *p, float nominal_period,
                   float trigger_thresh, float arm_thresh,
                   int64_t min_gap_us, float kp, float ki) {
    memset(p, 0, sizeof(*p));
    p->nominal_period = nominal_period;
    p->trigger_thresh = trigger_thresh;
    p->arm_thresh = arm_thresh;
    p->min_gap_us = min_gap_us;
    p->kp = kp;
    p->ki = ki;
    p->omega = 1.0f;
    p->armed = true;
    /* Absolute lock threshold: ~8% of nominal period in samples.
     * Fixed at init time so lock sensitivity doesn't drift with RPM. */
    p->lock_threshold = nominal_period * 0.08f;
}

bool edge_pll_update(edge_pll_t *p, float sample, int64_t ts_us) {
    /* Advance NCO. */
    p->theta += p->omega;
    if (p->theta >= p->nominal_period)
        p->theta -= p->nominal_period;

    /* Edge detection with hysteresis and minimum time gap. */
    bool edge = false;
    if (p->has_prev) {
        if (p->armed) {
            if (p->prev_sample >= p->trigger_thresh &&
                sample < p->trigger_thresh &&
                (ts_us - p->last_edge_ts) >= p->min_gap_us) {
                edge = true;
                p->armed = false;
                p->last_edge_ts = ts_us;
            }
        } else {
            if (sample > p->arm_thresh)
                p->armed = true;
        }
    }

    if (edge) {
        if (p->has_last_edge) {
            float raw_err = p->theta - p->last_edge_theta;
            float half = p->nominal_period * 0.5f;
            while (raw_err > half)  raw_err -= p->nominal_period;
            while (raw_err < -half) raw_err += p->nominal_period;

            /* PI controller. */
            p->integrator += p->ki * raw_err;
            if (p->integrator > INTEGRATOR_CLAMP)
                p->integrator = INTEGRATOR_CLAMP;
            if (p->integrator < -INTEGRATOR_CLAMP)
                p->integrator = -INTEGRATOR_CLAMP;

            float correction = p->kp * raw_err + p->integrator;
            p->omega += correction / p->nominal_period;

            /* Lock tracking via EMA of |phase error|. */
            float abs_err = raw_err < 0 ? -raw_err : raw_err;
            p->lock_ema = (1.0f - LOCK_EMA_ALPHA) * p->lock_ema +
                          LOCK_EMA_ALPHA * abs_err;
            p->locked = p->lock_ema < p->lock_threshold;
        }

        p->last_edge_theta = p->theta;
        p->has_last_edge = true;
        p->edge_count++;
    }

    p->prev_sample = sample;
    p->has_prev = true;

    return edge;
}

float edge_pll_theta_rad(const edge_pll_t *p) {
    float two_pi = 2.0f * (float)M_PI;
    return p->theta * two_pi / p->nominal_period;
}

float edge_pll_omega(const edge_pll_t *p) {
    return p->omega;
}

bool edge_pll_locked(const edge_pll_t *p) {
    return p->locked;
}
