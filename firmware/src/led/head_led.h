#pragma once

/*
 * Heading-indicator LED (meltybrain "stationary dot").
 *
 * The LED sits on PIN_HEAD_LED via a PN2222A (drive high = lit). When the
 * robot is spinning with a live heading estimate, the LED is pulsed once per
 * revolution as the estimated heading sweeps past a fixed reference angle.
 * To the eye that paints a single stationary bright dot the driver can use as
 * "front." When idle (not spinning, or no fresh estimate), it slow-blinks as
 * a heartbeat so you can see the firmware is alive.
 *
 * Heading is extrapolated from the last estimate using omega so the dot stays
 * crisp even though estimates arrive slower than the control loop.
 */

#include <stdint.h>
#include "estimation/heading_estimate.h"

void head_led_init(void);

/* Feed a fresh heading estimate (call when a new one is available). */
void head_led_on_estimate(const heading_estimate_t *est, uint32_t now_us);

/* Update the LED output. Call every control-loop iteration. */
void head_led_tick(uint32_t now_us);
