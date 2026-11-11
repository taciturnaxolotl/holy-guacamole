#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * RC link health. Pure logic (no pico headers) so tests/test_rc_health.c
 * runs the same code as the robot.
 *
 * The link is healthy while valid RC channel frames keep arriving. An ELRS
 * receiver on CRSF stops sending channel frames when it loses the
 * transmitter, so frame arrival is the direct measure of the link.
 *
 * This used to watch a checksum of the stick channels and call the link
 * stale when it had not changed for 3 s (PotatoMelt's rule, written for PWM
 * receivers that keep repeating the last pulse after a loss). On CRSF that
 * rule only adds false alarms: a pilot holding the sticks still in SPIN
 * mode sends identical frames for as long as they like.
 */

/* No valid channel frame for this long means the link is down. */
#define RC_LINK_TIMEOUT_MS 500

/* Reset to "no link". */
void rc_health_init(void);

/*
 * Feed the parser's frame bookkeeping once per control tick.
 *
 *   frame_seen     at least one valid channel frame has ever arrived.
 *   last_frame_ms  arrival time of the newest valid channel frame.
 *   now_ms         current time on the same clock.
 */
void rc_health_update(bool frame_seen, uint32_t last_frame_ms, uint32_t now_ms);

/* True if the link was healthy at the last rc_health_update(). */
bool rc_health_ok(void);
