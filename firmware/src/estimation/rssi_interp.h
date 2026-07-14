#pragma once

/*
 * RSSI sample interpolation to a uniform time grid.
 *
 * Raw ESP-NOW RSSI arrives at irregular intervals. This module
 * linearly interpolates onto a fixed-interval grid and stores
 * the result in a ring buffer. No DC removal here; consumers
 * handle that as needed (autocorr uses batch mean, edge PLL
 * works on raw interpolated values with its own thresholds).
 */

#include <stdint.h>
#include <stdbool.h>

#define RSSI_RING_SIZE 2048

typedef struct {
    uint32_t interval_us;

    float    buf[RSSI_RING_SIZE];
    uint32_t head;
    uint32_t count;

    float    prev_rssi;
    int64_t  prev_ts;
    bool     has_prev;
} rssi_interp_t;

void rssi_interp_init(rssi_interp_t *r, uint32_t interval_us);

/* Feed a raw RSSI sample. Produces zero or more interpolated outputs. */
void rssi_interp_push(rssi_interp_t *r, int8_t rssi, int64_t timestamp_us);

/* Total interpolated samples produced since init. */
uint32_t rssi_interp_count(const rssi_interp_t *r);

/* Read the most recent N samples into dst (newest first). */
uint32_t rssi_interp_read_recent(const rssi_interp_t *r,
                                 float *dst, uint32_t n);

/* Read a single sample by absolute count index.
 * Returns true if the index is within the ring buffer window. */
bool rssi_interp_read_at(const rssi_interp_t *r,
                         uint32_t abs_index, float *out);
