#include "rssi_uart.h"
#include <string.h>

void rssi_uart_init(rssi_uart_t *ru) {
    memset(ru, 0, sizeof(*ru));
}

bool rssi_uart_feed(rssi_uart_t *ru, uint8_t byte, heading_estimate_t *out) {
    /* Look for header sync. */
    if (!ru->synced) {
        if (ru->idx == 0 && byte == 0x55) {
            ru->buf[0] = byte;
            ru->idx = 1;
        } else if (ru->idx == 1 && byte == 0xAA) {
            ru->buf[1] = byte;
            ru->idx = 2;
            ru->synced = true;
        } else {
            ru->idx = 0;
        }
        return false;
    }

    /* Accumulate frame. */
    if (ru->idx < sizeof(ru->buf)) {
        ru->buf[ru->idx++] = byte;
    }

    /* Frame complete? */
    if (ru->idx >= sizeof(ru->buf)) {
        ru->idx = 0;
        ru->synced = false;

        /* Parse: theta (4), omega (4), locked (1), rssi (1). */
        float theta, omega;
        uint8_t locked;
        memcpy(&theta, &ru->buf[2], 4);
        memcpy(&omega, &ru->buf[6], 4);
        locked = ru->buf[10];

        out->heading = theta;
        out->omega = omega;
        out->alpha = 0.0f;  /* RSSI doesn't provide alpha */
        return true;
    }

    return false;
}

heading_estimate_t rssi_uart_get(const rssi_uart_t *ru) {
    /* Return a zeroed estimate — actual data comes via feed(). */
    heading_estimate_t est = {0};
    return est;
}
