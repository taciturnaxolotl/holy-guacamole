#include "rc_health.h"

#include "pico/stdlib.h"

static uint32_t last_checksum = 0;
static uint32_t last_change_ms = 0;
static bool initialized = false;

/* Weighted checksum of channel values. Different weights per channel
 * so that a change in any single channel is detectable even if others
 * are static. From PotatoMelt's approach. */
static uint32_t compute_checksum(const uint16_t channels[16]) {
    return (uint32_t)channels[0] * 64
         + (uint32_t)channels[1] * 16
         + (uint32_t)channels[2] * 4
         + (uint32_t)channels[3];
}

void rc_health_init(void) {
    last_checksum = 0;
    last_change_ms = to_ms_since_boot(get_absolute_time());
    initialized = true;
}

void rc_health_update(const uint16_t channels[16]) {
    if (!initialized) return;

    uint32_t cs = compute_checksum(channels);
    if (cs != last_checksum) {
        last_checksum = cs;
        last_change_ms = to_ms_since_boot(get_absolute_time());
    }
}

bool rc_health_ok(void) {
    if (!initialized) return false;
    uint32_t now = to_ms_since_boot(get_absolute_time());
    return (now - last_change_ms) < RC_STALE_TIMEOUT_MS;
}
