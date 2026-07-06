#pragma once

#include <stdint.h>
#include "hw_pins.h"

/* Initialize the SN74HC595 latch GPIOs (SEL_OE_N, SEL_LAT).
 * Must be called before any latch or SPI operations. */
void latch_init(void);

/* Shift a new byte into the latch and pulse SEL_LAT.
 * Does NOT change output enable state. Call latch_enable/disable separately. */
void latch_load(uint8_t image);

/* Enable latch outputs (drive SEL_OE_N low). */
void latch_enable(void);

/* Disable latch outputs (drive SEL_OE_N high, outputs go high-Z). */
void latch_disable(void);

/* Convenience: load + enable in one call. Use when you want to
 * atomically select a target and activate its output. */
void latch_select(uint8_t bit);

/* Convenience: load safe image + disable. All outputs inactive. */
void latch_deselect_all(void);

/* Get the current cached latch image. */
uint8_t latch_get_image(void);
