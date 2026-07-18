#pragma once

/*
 * RC channel map: which CRSF channel drives which robot control.
 *
 * This mirrors the control scheme validated in the SITL sim (sim/drive.c):
 * translation lives entirely on the right stick, there is no throttle stick
 * (spin power is a preset level set while armed), and the left stick X trims
 * the heading reference ("front").
 *
 * Channel order is the EdgeTX AETR layout from model05.yml (see
 * sim/zorro_detect.c). Radio channel N is 0-based index N-1. Verify with the
 * `chanmon` debug image.
 *
 *   idx 0  ch1  Aileron   Left stick X   -> heading trim
 *   idx 1  ch2  Elevator  Right stick Y  -> translation Y (fwd/back)
 *   idx 2  ch3  Throttle  Left stick Y   -> unused
 *   idx 3  ch4  Rudder    Right stick X  -> translation X (left/right)
 *   idx 4  ch5  SE        arm
 *   idx 7  ch8  SC        mode (STOP/SPIN/DRIFT)
 *   idx 9  ch10           attack button
 */

#include <stdint.h>
#include <stdbool.h>
#include "app/control_loop.h"   /* drive_mode_t */

/* Sticks (analog). Translation is the right stick; no throttle channel. */
#define RC_CH_STICK_X    3   /* ch4: right X -> drift vector x (left/right) */
#define RC_CH_STICK_Y    1   /* ch2: right Y -> drift vector y (fwd/back)   */
#define RC_CH_TRIM       0   /* ch1: left X  -> heading-trim nudge          */

/* Switches. */
#define RC_CH_ARM        4   /* ch5:  2/3-pos arm (high = armed)            */
#define RC_CH_MODE       7   /* ch8:  3-pos mode (STOP / SPIN / DRIFT)      */
#define RC_CH_ATTACK     9   /* ch10: momentary attack button              */

/* Spin power preset used whenever armed (no throttle stick), matching the
 * sim's "SPEED_HIGH while armed" behavior. */
#define RC_SPEED_ARMED   SPEED_HIGH

/* Position thresholds on the CRSF 172..1811 scale (center 992). */
#define RC_SW_LOW    640
#define RC_SW_HIGH   1360

static inline bool rc_switch_high(uint16_t v) { return v > RC_SW_HIGH; }

/* 3-position switch -> drive mode. Low=STOP, mid=SPIN, high=DRIFT. */
static inline drive_mode_t rc_mode(uint16_t v) {
    if (v < RC_SW_LOW)  return DRIVE_MODE_STOP;
    if (v > RC_SW_HIGH) return DRIVE_MODE_DRIFT;
    return DRIVE_MODE_SPIN;
}
