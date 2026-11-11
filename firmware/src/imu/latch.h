#pragma once

#include <stdint.h>
#include "hw_pins.h"

/* Initialize the SN74HC595 latch GPIOs (SEL_OE_N, SEL_LAT).
 * Must be called before any latch or SPI operations. */
void latch_init(void);

/* Shift a new byte into the latch and pulse SEL_LAT. Bit n of the image
 * drives output Q(A+n), so the LATCH_BIT_* numbers index it directly.
 * Does NOT change output enable state. Call latch_enable/disable separately.
 * Only call it with the outputs blanked: the latch shares SCK and MOSI
 * with the sensors, so a selected sensor would take the byte as data. */
void latch_load(uint8_t image);

/* Enable latch outputs (drive SEL_OE_N low). */
void latch_enable(void);

/* Disable latch outputs (drive SEL_OE_N high, outputs go high-Z). Every
 * CS line then returns high through its pull-up, which ends whatever SPI
 * transaction was open. */
void latch_disable(void);

/* Convenience: blank, load, enable. Releases any CS that was low before
 * pulling the new one low, so calling it again (even for the same bit)
 * starts a fresh SPI transaction on the target. */
void latch_select(uint8_t bit);

/* Convenience: load safe image + disable. All outputs inactive. */
void latch_deselect_all(void);
