#pragma once

#include <stdbool.h>
#include <stdint.h>

/*
 * Battery decision logic: warning hysteresis, halt persistence, halt latch.
 * Pure (no pico headers) so tests/test_battery_monitor.c runs the same code
 * as the robot. battery.c owns the ADC and feeds this the filtered cell
 * voltage. Header-only so the firmware picks it up without a new source
 * file in the build.
 *
 * Why not a plain threshold compare: the 380 mAh pack sags hard during
 * spin-up, so a healthy pack dips under the halt level for a moment and a
 * bare compare would cut the motors, let the pack recover, and spin up
 * again. The halt therefore needs the low reading to persist, and once it
 * trips it stays tripped until the operator commands a disarm with the
 * pack back above the halt level at rest.
 */

/* Per-cell voltage thresholds (volts). */
#define BATTERY_WARN_V   3.75f
#define BATTERY_HALT_V   3.60f

/* A flag set at its threshold clears only this far above it, so a reading
 * sitting on the threshold cannot flicker the flag. */
#define BATTERY_HYST_V   0.10f

/* The cell voltage must stay under BATTERY_HALT_V this long to halt. Long
 * enough to ride through spin-up sag, short next to the time it takes to
 * damage a pack at 3.6 V/cell. The hardware UVLO (about 8.0 V, 2.67 V/cell)
 * still backs this up with no delay. */
#define BATTERY_HALT_PERSIST_MS 1500u

typedef struct {
    bool     low;              /* warning, with hysteresis */
    bool     halted;           /* latched halt */
    bool     below;            /* cell voltage is under the halt level now */
    uint32_t below_since_ms;   /* when it went under; valid while `below` */
} battery_monitor_t;

static inline void battery_monitor_init(battery_monitor_t *m) {
    m->low = false;
    m->halted = false;
    m->below = false;
    m->below_since_ms = 0;
}

/*
 * Advance the monitor.
 *
 *   cell_v       filtered per-cell voltage.
 *   now_ms       monotonic milliseconds; differences are taken modulo 2^32.
 *   disarm_cmd   the operator is holding the arm switch low on a healthy
 *                link. Only this, with the pack recovered, releases a halt,
 *                and the arming interlock then needs a fresh low-to-high
 *                move, so a recovering pack never restarts the spin.
 */
static inline void battery_monitor_update(battery_monitor_t *m, float cell_v,
                                          uint32_t now_ms, bool disarm_cmd) {
    if (cell_v < BATTERY_WARN_V) {
        m->low = true;
    } else if (cell_v >= BATTERY_WARN_V + BATTERY_HYST_V) {
        m->low = false;
    }

    if (cell_v < BATTERY_HALT_V) {
        if (!m->below) {
            m->below = true;
            m->below_since_ms = now_ms;
        }
        if ((uint32_t)(now_ms - m->below_since_ms) >= BATTERY_HALT_PERSIST_MS) {
            m->halted = true;
        }
    } else {
        m->below = false;
    }

    if (m->halted && disarm_cmd && cell_v >= BATTERY_HALT_V + BATTERY_HYST_V) {
        m->halted = false;
    }
}

/* False once the halt has latched. */
static inline bool battery_monitor_ok(const battery_monitor_t *m) {
    return !m->halted;
}

static inline bool battery_monitor_low(const battery_monitor_t *m) {
    return m->low;
}
