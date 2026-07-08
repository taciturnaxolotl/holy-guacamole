#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * RC signal health monitor. Belt-and-suspenders safety layer on top of
 * the receiver's own failsafe. Computes a checksum of all channel values;
 * if the checksum hasn't changed for longer than the timeout, the link
 * is considered stale even if the receiver reports "alive."
 *
 * Call rc_health_update() every time new CRSF data arrives. Check
 * rc_health_ok() before trusting stick inputs.
 */

/* Timeout in ms. If no channel change is detected for this long, the
 * link is considered stale. PotatoMelt uses 3000ms. */
#define RC_STALE_TIMEOUT_MS 3000

/* Initialize the health monitor. */
void rc_health_init(void);

/* Call with the current CRSF channel array whenever a frame arrives. */
void rc_health_update(const uint16_t channels[16]);

/* Returns true if the RC link appears healthy (channels changing or
 * recently changed within the timeout). */
bool rc_health_ok(void);
