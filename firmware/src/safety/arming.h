#pragma once

#include <stdbool.h>

/*
 * Arming interlock. Pure logic, no pico headers, so the host tests in
 * tests/test_arming.c run the exact code the robot does.
 *
 * The arm switch level alone must never spin the robot up: a boot or
 * watchdog reset with the switch already high, a link that comes back
 * after a failsafe, or a battery that recovers after a halt would all
 * start a 4000 rpm spin that nobody asked for. Arming therefore needs a
 * deliberate gesture: the switch seen LOW while everything is healthy,
 * followed by a move to HIGH. Any fault throws the interlock back to
 * LOCKED, so the gesture has to be repeated after the fault clears.
 *
 * Header-only so the firmware picks it up without a new source file in
 * the build.
 */

typedef enum {
    ARMING_LOCKED = 0,   /* disarmed; switch must be seen low while healthy */
    ARMING_READY,        /* disarmed; switch was low, a move to high arms   */
    ARMING_ARMED,
} arming_state_t;

typedef struct {
    arming_state_t state;
} arming_t;

/* Starts disarmed and locked. */
static inline void arming_init(arming_t *a) {
    a->state = ARMING_LOCKED;
}

/*
 * Advance the interlock one control tick and return true while armed.
 *
 *   healthy  every arming precondition holds (sensor, RC link, battery,
 *            fresh estimate). The caller must only report a switch
 *            position when the link is healthy: with no frames the
 *            channels read 0, which looks like a low switch.
 *   sw_low   arm switch is at its low stop.
 *   sw_high  arm switch is at its high stop.
 *
 * Neither flag set is the middle of a 3-position switch (or a value in
 * the dead band). It disarms, but it does not count as the low that
 * re-enables arming, so jitter around the high threshold cannot re-arm.
 * A switch travelling low -> mid -> high still arms.
 */
static inline bool arming_update(arming_t *a, bool healthy, bool sw_low,
                                 bool sw_high) {
    if (!healthy) {
        a->state = ARMING_LOCKED;
    } else if (sw_low) {
        a->state = ARMING_READY;
    } else if (!sw_high) {
        if (a->state == ARMING_ARMED) a->state = ARMING_LOCKED;
    } else if (a->state == ARMING_READY) {
        a->state = ARMING_ARMED;
    }
    return a->state == ARMING_ARMED;
}

static inline bool arming_is_armed(const arming_t *a) {
    return a->state == ARMING_ARMED;
}
