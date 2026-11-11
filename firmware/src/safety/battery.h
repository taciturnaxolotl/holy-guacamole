#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "safety/battery_monitor.h"   /* thresholds and the decision logic */

/*
 * Battery voltage monitor with low-voltage alert and safety halt.
 *
 * Core 0 reads the VBAT ADC divider on its sensor tick and filters it with
 * an exponential moving average. Core 1 turns the filtered cell voltage
 * into the warning and halt flags once per control tick (battery_update),
 * so all the decision state lives on one core.
 *
 * Thresholds are per-cell for the 3S HV pack (GNB 380, 4.35 V/cell full)
 * and live in battery_monitor.h with the logic that uses them. The warning
 * flag is for the LED/status system. The halt cuts the motors after the
 * low reading has persisted, then stays latched until the operator disarms
 * with the pack recovered.
 */

#define BATTERY_CELLS    3       /* 3S HV pack; the board is 3S-only (no UVLO jumper) */

/* Initialize ADC and prime the filter. Call from core 0 init. */
void battery_init(void);

/* Sample the ADC and update the filtered voltage. Call once per sensor
 * tick (~1kHz) from core 0. */
void battery_sample(void);

/* Re-evaluate the warning and halt flags from the filtered voltage. Call
 * once per control tick from core 1. disarm_cmd is true while the operator
 * holds the arm switch low on a healthy link; see battery_monitor.h. */
void battery_update(uint32_t now_ms, bool disarm_cmd);

/* False once the low-voltage halt has latched. Core 1 only; reflects the
 * last battery_update(). */
bool battery_ok(void);

/* True while the low-voltage warning is active. Core 1 only; reflects the
 * last battery_update(). */
bool battery_low(void);

/* Current filtered pack voltage in volts. */
float battery_voltage(void);

/* Current filtered per-cell voltage in volts. */
float battery_cell_voltage(void);
