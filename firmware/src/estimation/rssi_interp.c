#include "rssi_interp.h"

#include <string.h>

#define MAX_GAP_US 100000

void rssi_interp_init(rssi_interp_t *r, uint32_t interval_us) {
    memset(r, 0, sizeof(*r));
    r->interval_us = interval_us;
}

void rssi_interp_push(rssi_interp_t *r, int8_t rssi, int64_t timestamp_us) {
    float frssi = (float)rssi;

    if (!r->has_prev) {
        r->prev_rssi = frssi;
        r->prev_ts = timestamp_us;
        r->has_prev = true;
        return;
    }

    int64_t gap = timestamp_us - r->prev_ts;
    if (gap <= 0 || gap > MAX_GAP_US) {
        r->prev_rssi = frssi;
        r->prev_ts = timestamp_us;
        return;
    }

    int64_t target_ts = r->prev_ts + (int64_t)r->interval_us;

    while (target_ts <= timestamp_us) {
        float ratio = (float)(target_ts - r->prev_ts) / (float)gap;
        float val = r->prev_rssi + ratio * (frssi - r->prev_rssi);

        r->buf[r->head] = val;
        r->head = (r->head + 1) % RSSI_RING_SIZE;
        r->count++;

        target_ts += (int64_t)r->interval_us;
    }

    r->prev_rssi = frssi;
    r->prev_ts = timestamp_us;
}

uint32_t rssi_interp_count(const rssi_interp_t *r) {
    return r->count;
}

uint32_t rssi_interp_read_recent(const rssi_interp_t *r,
                                 float *dst, uint32_t n) {
    uint32_t avail = r->count < RSSI_RING_SIZE ? r->count : RSSI_RING_SIZE;
    if (n > avail) n = avail;

    for (uint32_t i = 0; i < n; i++) {
        uint32_t idx = (r->head - 1 - i + RSSI_RING_SIZE) % RSSI_RING_SIZE;
        dst[i] = r->buf[idx];
    }
    return n;
}

bool rssi_interp_read_at(const rssi_interp_t *r,
                         uint32_t abs_index, float *out) {
    uint32_t avail = r->count < RSSI_RING_SIZE ? r->count : RSSI_RING_SIZE;
    uint32_t oldest = r->count - avail;

    if (abs_index < oldest || abs_index >= r->count)
        return false;

    uint32_t offset_from_head = r->count - 1 - abs_index;
    uint32_t idx = (r->head - 1 - offset_from_head + RSSI_RING_SIZE) % RSSI_RING_SIZE;
    *out = r->buf[idx];
    return true;
}
