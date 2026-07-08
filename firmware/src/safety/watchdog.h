#pragma once

#include <stdint.h>

/*
 * Hardware watchdog for the RP2350. If the main loop stops feeding the
 * watchdog within the timeout period, the chip resets. This prevents a
 * firmware hang from leaving motors spinning uncontrolled on a meltybrain.
 *
 * The watchdog must be updated from BOTH cores if both are running,
 * since either core hanging is a failure condition. Core 0 updates via
 * watchdog_feed(), core 1 via watchdog_feed_core1().
 */

/* Initialize and start the hardware watchdog with the given timeout in ms.
 * Call once from core 1 (main) before launching core 0. */
void watchdog_start(uint32_t timeout_ms);

/* Feed the watchdog from core 0. Must be called at least once per
 * timeout period. Place in the sensor loop. */
void watchdog_feed(void);

/* Feed the watchdog from core 1. Must be called at least once per
 * timeout period. Place in the control loop. */
void watchdog_feed_core1(void);
