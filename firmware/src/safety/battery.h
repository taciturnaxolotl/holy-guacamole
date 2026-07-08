#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * Battery voltage monitor with low-voltage alert and safety halt.
 *
 * Reads the VBAT ADC divider on core 0's sensor tick, filters with an
 * exponential moving average, and exposes the current cell voltage.
 * Core 1 checks battery_ok() before commanding motors; if voltage is
 * critically low, motors are cut regardless of stick input.
 *
 * Thresholds are per-cell for a 2S pack (configurable). The alert level
 * triggers a warning flag the LED/status system can display; the halt
 * level cuts motors immediately.
 */

/* Per-cell voltage thresholds (volts). */
#define BATTERY_WARN_V   3.75f
#define BATTERY_HALT_V   3.60f
#define BATTERY_CELLS    2       /* 2S pack */

/* Initialize ADC and start background sampling. Call from core 0 init. */
void battery_init(void);

/* Sample the ADC and update the filtered voltage. Call once per sensor
 * tick (~1kHz) from core 0. */
void battery_sample(void);

/* Returns true if battery voltage is above the halt threshold.
 * Core 1 should check this before commanding motors. */
bool battery_ok(void);

/* Returns true if battery voltage is below the warning threshold. */
bool battery_low(void);

/* Current filtered pack voltage in volts. */
float battery_voltage(void);

/* Current filtered per-cell voltage in volts. */
float battery_cell_voltage(void);
