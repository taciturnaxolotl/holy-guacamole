/*
 * RSSI heading sensor source (UART from ESP32-C3).
 *
 * Receives binary frames from the ESP32-C3 over UART, parses them
 * into heading_estimate_t, and feeds them into the sensor dispatch.
 */

#include "sensor_source.h"
#include "rssi_uart.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "pico/time.h"
#include <string.h>

#define UART_ID       uart1
#define UART_BAUD     115200
#define UART_TX_PIN   23  /* SWDIO on XIAO RP2350 carrier */
#define UART_RX_PIN   24  /* SWDCK on XIAO RP2350 carrier */

static rssi_uart_t ru;
static heading_estimate_t last_est;
static bool initialized;

static bool rssi_init(void) {
    uart_init(UART_ID, UART_BAUD);
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    rssi_uart_init(&ru);
    memset(&last_est, 0, sizeof(last_est));
    initialized = true;
    return true;
}

static heading_estimate_t rssi_tick(float dt) {
    if (!initialized) return last_est;

    /* Drain UART RX buffer. */
    while (uart_is_readable(UART_ID)) {
        uint8_t byte = uart_getc(UART_ID);
        heading_estimate_t tmp;
        if (rssi_uart_feed(&ru, byte, &tmp)) {
            last_est = tmp;
        }
    }

    return last_est;
}

const sensor_source_t sensor_rssi = {
    .name  = "RSSI-UART",
    .init  = rssi_init,
    .tick  = rssi_tick,
    .feed  = NULL,
};
