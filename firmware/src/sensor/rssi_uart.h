#pragma once

/*
 * RSSI heading receiver over UART from ESP32-C3.
 *
 * Parses the binary protocol from esp-rssi and provides
 * a heading_estimate_t compatible with the rest of the firmware.
 */

#include <stdint.h>
#include <stdbool.h>
#include "estimation/heading_estimate.h"

typedef struct {
    uint8_t  buf[12];   /* UART frame buffer */
    uint8_t  idx;       /* Current parse position */
    bool     synced;    /* True if header (0x55 0xAA) found */
} rssi_uart_t;

void rssi_uart_init(rssi_uart_t *ru);

/* Feed a byte from UART RX. Returns true if a complete frame was parsed. */
bool rssi_uart_feed(rssi_uart_t *ru, uint8_t byte, heading_estimate_t *out);

/* Get latest estimate (non-blocking, returns last valid). */
heading_estimate_t rssi_uart_get(const rssi_uart_t *ru);
