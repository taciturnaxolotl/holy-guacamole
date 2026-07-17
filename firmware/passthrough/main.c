/*
 * ELRS passthrough firmware for the XIAO RP2350.
 *
 * TEMPORARY tool image, not the flight controller. Flash this, use it to
 * flash/configure the ELRS receiver wired to uart0, then flash the real
 * firmware back (picotool load -x build/holy_guacamole.uf2).
 *
 * The ELRS receiver's UART is the only thing on uart0 (GPIO0 = TX -> RX's
 * RX, GPIO1 = RX <- RX's TX, per include/hw_pins.h). This firmware makes the
 * RP2350 sit exactly where a Betaflight flight controller would, so the
 * ExpressLRS Configurator's "BetaflightPassthrough" method works against it
 * with no extra hardware:
 *
 *   1. The Configurator opens our USB CDC port and runs a tiny CLI dialogue
 *      (#, get serialrx_provider, get serialrx_inverted, get
 *      serialrx_halfduplex, get rx_spi_protocol, serial, serialpassthrough).
 *      We answer exactly what BFinitPassthrough.py checks for.
 *   2. On "serialpassthrough" we drop into a transparent USB<->uart0 bridge
 *      and mirror the host's requested baud onto uart0.
 *   3. The Configurator then sends the ROM training burst + the CRSF
 *      reboot-to-bootloader command (ec 04 32 62 6c ..) through the bridge,
 *      and esptool flashes the receiver over the same wire.
 *
 * We deliberately do NOT forward uart0 -> USB until passthrough is active,
 * so the receiver's normal CRSF chatter can't corrupt the CLI dialogue.
 */

#include <string.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "tusb.h"
#include "hw_pins.h"   /* PIN_CRSF_TX/RX, CRSF_UART, CRSF_BAUD */

/* Default line rate before the host requests one; ELRS CRSF is 420000. */
#define DEFAULT_BAUD  CRSF_BAUD

typedef enum { MODE_CLI, MODE_PASS } mode_t;

static mode_t mode = MODE_CLI;
static char   line[128];
static size_t line_len;

/* ---- USB CDC helpers ---- */

static void cdc_str(const char *s) {
    tud_cdc_write(s, strlen(s));
    tud_cdc_write_flush();
}

/* ---- Minimal Betaflight CLI emulation (CLI phase only) ----
 *
 * Responses are shaped to satisfy the exact substring / regex checks in
 * ExpressLRS's BFinitPassthrough.py + SerialHelper.py:
 *   - _validate_serialrx() reads until "# " and looks for " = <value>".
 *   - serial detection reads \n-delimited lines and regex-matches
 *     'serial (\d+) (\d+) ' with the 2nd field's bit 0x40 (Serial RX) set.
 */
static void handle_line(const char *l) {
    if (strncmp(l, "get serialrx_provider", 21) == 0) {
        cdc_str("serialrx_provider = CRSF\r\n# ");
    } else if (strncmp(l, "get serialrx_inverted", 21) == 0) {
        cdc_str("serialrx_inverted = OFF\r\n# ");
    } else if (strncmp(l, "get serialrx_halfduplex", 23) == 0) {
        cdc_str("serialrx_halfduplex = OFF\r\n# ");
    } else if (strncmp(l, "get rx_spi_protocol", 19) == 0) {
        /* Must NOT contain " = EXPRESSLRS" or the script assumes SPI RX. */
        cdc_str("rx_spi_protocol = AUTO\r\n# ");
    } else if (strncmp(l, "serialpassthrough", 17) == 0) {
        /* Enter transparent bridge. Baud is mirrored from CDC line coding
         * when the host reopens the port, but honor the requested value now
         * too in case it doesn't. */
        long baud = DEFAULT_BAUD;
        const char *p = l;
        while (*p && (*p < '0' || *p > '9')) p++;   /* skip "serialpassthrough" */
        while (*p >= '0' && *p <= '9') p++;          /* skip UART index */
        while (*p == ' ') p++;
        if (*p) baud = strtol(p, NULL, 10);
        if (baud > 0) uart_set_baudrate(CRSF_UART, (uint)baud);
        /* Drop stale CRSF bytes so the bridge starts clean. */
        while (uart_is_readable(CRSF_UART)) (void)uart_getc(CRSF_UART);
        mode = MODE_PASS;
    } else if (strcmp(l, "serial") == 0) {
        /* One Serial-RX port: index 0, function bitmask 64 (bit 0x40). The
         * trailing space matters: the script's regex requires it. */
        cdc_str("serial 0 64 115200 57600 0 115200\r\n# ");
    }
    /* Unknown commands: stay quiet; the script only depends on the above. */
}

static void cli_rx(uint8_t b) {
    if (b == '#' && line_len == 0) {
        /* Initial CLI wake: reply with a prompt ending in "# ". */
        cdc_str("\r\n# ");
        return;
    }
    if (b == '\n' || b == '\r') {
        if (line_len) {
            line[line_len] = '\0';
            handle_line(line);
            line_len = 0;
        }
        return;
    }
    if (line_len < sizeof(line) - 1) line[line_len++] = (char)b;
}

/* ---- Transparent bridge ---- */

static void bridge(void) {
    uint8_t buf[64];

    /* USB -> uart0 */
    while (tud_cdc_available()) {
        uint32_t n = tud_cdc_read(buf, sizeof(buf));
        uart_write_blocking(CRSF_UART, buf, n);
    }

    /* uart0 -> USB */
    size_t n = 0;
    while (uart_is_readable(CRSF_UART) && n < sizeof(buf)) {
        buf[n++] = uart_getc(CRSF_UART);
    }
    if (n) {
        tud_cdc_write(buf, n);
        tud_cdc_write_flush();
    }
}

/* TinyUSB callback: mirror the host's requested baud onto uart0 once we're
 * bridging. During the CLI phase the CDC baud is irrelevant to uart0. */
void tud_cdc_line_coding_cb(uint8_t itf, cdc_line_coding_t const *coding) {
    (void)itf;
    if (mode == MODE_PASS && coding->bit_rate > 0) {
        uart_set_baudrate(CRSF_UART, coding->bit_rate);
    }
}

int main(void) {
    /* uart0 to the ELRS receiver. */
    uart_init(CRSF_UART, DEFAULT_BAUD);
    gpio_set_function(PIN_CRSF_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_CRSF_RX, GPIO_FUNC_UART);
    uart_set_hw_flow(CRSF_UART, false, false);
    uart_set_format(CRSF_UART, 8, 1, UART_PARITY_NONE);
    uart_set_fifo_enabled(CRSF_UART, true);

    tusb_init();

    while (1) {
        tud_task();
        if (mode == MODE_CLI) {
            while (tud_cdc_available()) {
                uint8_t b;
                if (tud_cdc_read(&b, 1) == 1) cli_rx(b);
            }
        } else {
            bridge();
        }
    }
}
