#include "crsf.h"
#include "hw_pins.h"

#include "hardware/uart.h"
#include "pico/stdlib.h"

/* CRSF frame types */
#define CRSF_TYPE_RC_CHANNELS   0x16
#define CRSF_TYPE_LINK_STATS    0x14

/* CRSF sync byte */
#define CRSF_SYNC               0xC8

/* Frame buffer */
#define CRSF_MAX_FRAME_LEN      64

static uint8_t rx_buf[CRSF_MAX_FRAME_LEN];
static uint8_t rx_pos = 0;

void crsf_init(void) {
    uart_init(CRSF_UART, CRSF_BAUD);
    gpio_set_function(PIN_CRSF_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_CRSF_RX, GPIO_FUNC_UART);
    uart_set_hw_flow(CRSF_UART, false, false);
    uart_set_format(CRSF_UART, 8, 1, UART_PARITY_NONE);
}

/* CRSF CRC8 (poly 0xD5) */
static uint8_t crsf_crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0xD5;
            else
                crc <<= 1;
        }
    }
    return crc;
}

static void parse_rc_channels(const uint8_t *payload, uint8_t payload_len, crsf_state_t *state) {
    /* 22 bytes of packed 11-bit channel values */
    if (payload_len < 22) return;

    const uint8_t *p = payload;
    const uint8_t *end = payload + 22;
    uint32_t bits = 0;
    int bit_pos = 0;

    for (int ch = 0; ch < CRSF_NUM_CHANNELS; ch++) {
        while (bit_pos < 11) {
            if (p >= end) return;  /* malformed frame */
            bits |= ((uint32_t)*p++) << bit_pos;
            bit_pos += 8;
        }
        state->channels[ch] = bits & 0x7FF;
        bits >>= 11;
        bit_pos -= 11;
    }
    state->valid = true;
    state->last_frame_ms = to_ms_since_boot(get_absolute_time());
}

static void parse_link_stats(const uint8_t *payload, crsf_state_t *state) {
    state->rssi_dbm = -(int8_t)payload[0];
    state->link_quality = payload[1];
}

static void process_frame(const uint8_t *frame, uint8_t len, crsf_state_t *state) {
    /* frame[0] = type, frame[1..len-2] = payload, frame[len-1] = CRC */
    if (len < 2) return;

    uint8_t type = frame[0];
    uint8_t payload_len = len - 2;  /* subtract type and CRC */
    const uint8_t *payload = &frame[1];

    /* Verify CRC over type + payload */
    uint8_t crc = crsf_crc8(frame, len - 1);
    if (crc != frame[len - 1]) return;

    switch (type) {
        case CRSF_TYPE_RC_CHANNELS:
            if (payload_len == 22) parse_rc_channels(payload, payload_len, state);
            break;
        case CRSF_TYPE_LINK_STATS:
            if (payload_len >= 2) parse_link_stats(payload, state);
            break;
    }
}

void crsf_poll(crsf_state_t *state) {
    while (uart_is_readable(CRSF_UART)) {
        uint8_t byte = uart_getc(CRSF_UART);

        if (rx_pos == 0) {
            /* Looking for sync byte */
            if (byte == CRSF_SYNC) {
                rx_pos = 1;
            }
            continue;
        }

        if (rx_pos == 1) {
            /* Frame length (includes type + payload + CRC) */
            if (byte < 2 || byte > CRSF_MAX_FRAME_LEN - 2) {
                rx_pos = 0;
                continue;
            }
            rx_buf[0] = byte;
            rx_pos = 2;
            continue;
        }

        /* Accumulate frame body */
        rx_buf[rx_pos - 1] = byte;
        rx_pos++;

        uint8_t frame_len = rx_buf[0];
        if (rx_pos - 1 >= frame_len + 1) {
            /* Complete frame: rx_buf[0]=len, rx_buf[1..frame_len]=type+payload+CRC */
            process_frame(&rx_buf[1], frame_len, state);
            rx_pos = 0;
        }
    }
}

bool crsf_link_alive(const crsf_state_t *state, uint32_t timeout_ms) {
    if (!state->valid) return false;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    return (now - state->last_frame_ms) < timeout_ms;
}
