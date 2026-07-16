#pragma once

/*
 * RadioMaster Zorro input abstraction for the SITL simulator.
 *
 * On macOS, reads the Zorro's raw HID report via IOKit instead of
 * raylib's gamepad API (which doesn't expose the EdgeTX axes properly).
 * EdgeTX classic joystick mode maps channelOutputs[0..7] to 8 16-bit
 * LE axes, and channels 8+ to button bits. The model's mixData
 * determines which physical control feeds each channel.
 *
 * For model05.yml (AETR, mode 2):
 *
 *   raylib axis 0 = CH0 = Ail  = Left stick X
 *   raylib axis 1 = CH1 = Ele  = Right stick Y
 *   raylib axis 2 = CH2 = Thr  = Left stick Y
 *   raylib axis 3 = CH3 = Rud  = Right stick X
 *
 *   raylib axis 4 = CH4 = SE switch (3-pos, analog: -1/0/+1)
 *   raylib axis 5 = CH5 = SF switch (2-pos safety, analog: -1/+1)
 *   raylib axis 6 = CH6 = SB switch (3-pos)
 *   raylib axis 7 = CH7 = SC switch (3-pos)
 *
 * Switches SA, SD, SG, SH are on CH8-CH11 → button bits.
 * S1/S2 knobs are on CH12/CH13 → button bits (6-pos encoders).
 *
 * Buttons in EdgeTX classic mode start at byte 19 of the HID report.
 * CH8 maps to button 0, CH9 to button 1, etc. raylib exposes these
 * as gamepad buttons 0-7 (the first 8 button bits).
 *
 *   raylib btn 0 = CH8  = SA switch
 *   raylib btn 1 = CH9  = SD switch
 *   raylib btn 2 = CH10 = SG switch
 *   raylib btn 3 = CH11 = SH switch
 *   raylib btn 4 = CH12 = S1 knob (6-pos, discrete bits)
 *   raylib btn 5 = CH13 = S2 knob (6-pos, discrete bits)
 *
 * NOTE: raylib on macOS may remap gamepad axes/buttons to an XInput
 * layout via the Gamepad axis mapping. The actual indices may differ
 * from the raw EdgeTX channel order. Use zorro_debug_dump() to verify
 * on your system, then adjust ZORRO_AXIS_* / ZORRO_BTN_* if needed.
 */

#include <stdbool.h>
#include <stdint.h>

/* Axis byte offsets in the EdgeTX classic HID report (16-bit LE each). */
#define ZORRO_AXIS_LSTICK_X  3   /* CH0 Ail */
#define ZORRO_AXIS_RSTICK_Y  5   /* CH1 Ele */
#define ZORRO_AXIS_LSTICK_Y  7   /* CH2 Thr */
#define ZORRO_AXIS_RSTICK_X  9   /* CH3 Rud */
#define ZORRO_AXIS_SE       11   /* CH4 SE switch (3-pos) */
#define ZORRO_AXIS_SF       13   /* CH5 SF safety (2-pos) */
#define ZORRO_AXIS_SB       15   /* CH6 SB switch (3-pos) */
#define ZORRO_AXIS_SC       17   /* CH7 SC switch (3-pos) */

/* Button bit indices within byte 19 of the EdgeTX classic HID report. */
#define ZORRO_BTN_SA         0   /* CH8  SA */
#define ZORRO_BTN_SD         1   /* CH9  SD */
#define ZORRO_BTN_SG         2   /* CH10 SG */
#define ZORRO_BTN_SH         3   /* CH11 SH */
#define ZORRO_BTN_S1         4   /* CH12 S1 knob (6-pos) */
#define ZORRO_BTN_S2         5   /* CH13 S2 knob (6-pos) */

/* Deadband for analog stick noise. */
#define ZORRO_STICK_DEADBAND 0.10f

typedef struct {
    float lstick_x;      /* [-1,1] */
    float lstick_y;      /* [-1,1] */
    float rstick_x;      /* [-1,1] */
    float rstick_y;      /* [-1,1] */
    float se_switch;     /* [-1,0,+1] 3-pos */
    float sf_switch;     /* [-1,+1] 2-pos safety */
    float sb_switch;     /* [-1,0,+1] 3-pos */
    float sc_switch;     /* [-1,0,+1] 3-pos */
    bool  sa_pressed;    /* momentary */
    bool  sd_pressed;
    bool  sg_pressed;
    bool  sh_pressed;
    bool  s1_pressed;     /* 6-pos knob (any position active) */
    bool  s2_pressed;
    bool  gamepad_present;
} zorro_input_t;

/* Read the current Zorro state via IOKit HID.
 * Call once per frame before consuming the values. */
zorro_input_t zorro_read(void);

/* Print raw axis/button values for binding verification. */
void zorro_debug_dump(const zorro_input_t *z);
