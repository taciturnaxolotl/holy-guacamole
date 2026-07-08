#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "hardware/pio.h"

/* DSHOT throttle command range */
#define DSHOT_MIN_THROTTLE  48
#define DSHOT_MAX_THROTTLE  2047
#define DSHOT_STOP          0

/* Motor pole count for RPM calculation (D2822: 14 poles = 7 pole pairs) */
#define MOTOR_POLE_PAIRS    7

/* Telemetry types from AM32 EDT */
#define DSHOT_EXT_TELE_TEMP     0x02
#define DSHOT_EXT_TELE_VOLTAGE  0x04
#define DSHOT_EXT_TELE_CURRENT  0x06

typedef struct {
    uint32_t erpm_period_us;
    uint32_t rpm;
    uint8_t  temperature_c;
    uint16_t voltage_cv;      /* centivolts (V * 100) */
    uint8_t  current_a;
    uint16_t reads;
    uint16_t errors;
} dshot_telemetry_t;

typedef struct {
    PIO      pio;
    uint     sm;
    uint     gpio;
    bool     initialized;
    dshot_telemetry_t telemetry;
} dshot_esc_t;

/* Load the DSHOT PIO program once. Must be called before dshot_init.
 * Returns true on success. Safe to call multiple times (idempotent). */
bool dshot_load_program(PIO pio);

/* Initialize a bidirectional DSHOT600 ESC on the given GPIO.
 * Each ESC needs its own PIO state machine. Returns true on success.
 * dshot_load_program must have been called first. */
bool dshot_init(dshot_esc_t *esc, PIO pio, uint gpio);

/* Send a raw DSHOT command (0-2047). Must be called at >= 200Hz. */
void dshot_send(dshot_esc_t *esc, uint16_t command);

/* Set throttle as a fraction [0.0, 1.0]. Maps to DSHOT command range. */
void dshot_set_throttle(dshot_esc_t *esc, float throttle);

/* Check for and decode pending telemetry. Returns true if new data available. */
bool dshot_read_telemetry(dshot_esc_t *esc);
