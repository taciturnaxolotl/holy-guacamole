#pragma once

#include <stdint.h>
#include <stdbool.h>

#define CRSF_NUM_CHANNELS 16

/* Standard CRSF channel range: 172-1811 maps to 988-2012us */
#define CRSF_CH_MIN   172
#define CRSF_CH_MAX   1811
#define CRSF_CH_MID   992

typedef struct {
    uint16_t channels[CRSF_NUM_CHANNELS];
    uint8_t  link_quality;     /* 0-100 */
    int8_t   rssi_dbm;         /* negative dBm */
    bool     valid;            /* true if last frame decoded OK */
    uint32_t last_frame_ms;    /* timestamp of last valid frame */
} crsf_state_t;

/* Initialize CRSF UART on GPIO0/GPIO1 at 420000 baud. */
void crsf_init(void);

/* Poll for new CRSF frames. Updates state if a valid frame is received.
 * Call this frequently (e.g. every ms) from core 1. */
void crsf_poll(crsf_state_t *state);

/* Check if RC link is alive (received frame within timeout). */
bool crsf_link_alive(const crsf_state_t *state, uint32_t timeout_ms);
