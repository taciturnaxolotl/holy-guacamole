#include "rc_health.h"

static bool     link_ok;
static bool     lost;            /* timed out; waiting for a newer frame */
static uint32_t lost_frame_ms;   /* the frame timestamp that timed out */

void rc_health_init(void) {
    link_ok = false;
    lost = false;
    lost_frame_ms = 0;
}

void rc_health_update(bool frame_seen, uint32_t last_frame_ms, uint32_t now_ms) {
    if (!frame_seen) {
        link_ok = false;
        return;
    }

    /* Once a frame has timed out, only a newer frame brings the link back.
     * Without this the 32-bit age would wrap after 49.7 days of silence and
     * make the dead link look alive for one timeout period. */
    if (lost) {
        if (last_frame_ms == lost_frame_ms) {
            link_ok = false;
            return;
        }
        lost = false;
    }

    /* Signed so a frame stamped a moment after now_ms was sampled reads as
     * fresh rather than as a huge unsigned age. */
    int32_t age_ms = (int32_t)(now_ms - last_frame_ms);
    if (age_ms >= RC_LINK_TIMEOUT_MS) {
        lost = true;
        lost_frame_ms = last_frame_ms;
        link_ok = false;
        return;
    }
    link_ok = true;
}

bool rc_health_ok(void) {
    return link_ok;
}
