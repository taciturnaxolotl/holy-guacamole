#include "watchdog.h"

#include <stdint.h>
#include "hardware/watchdog.h"
#include "hardware/sync.h"

/* Dual-core watchdog coordination via spinlock. Both cores must signal
 * alive within the timeout period or the chip resets. A spinlock
 * serializes the flag exchange so there's no TOCTOU race between cores.
 * Without this, ARM store buffering could cause both cores to miss each
 * other's flag and trigger a spurious reset. */

static volatile bool core0_alive = false;
static volatile bool core1_alive = false;
static spin_lock_t *wdt_lock = NULL;

void watchdog_start(uint32_t timeout_ms) {
    int lock_num = spin_lock_claim_unused(true);
    wdt_lock = spin_lock_instance(lock_num);
    watchdog_enable(timeout_ms, true);  /* pause-on-debug */
}

void watchdog_feed(void) {
    if (!wdt_lock) return;
    uint32_t irq = spin_lock_blocking(wdt_lock);
    core0_alive = true;
    if (core1_alive) {
        watchdog_update();
        core0_alive = false;
        core1_alive = false;
    }
    spin_unlock(wdt_lock, irq);
}

void watchdog_feed_core1(void) {
    if (!wdt_lock) return;
    uint32_t irq = spin_lock_blocking(wdt_lock);
    core1_alive = true;
    if (core0_alive) {
        watchdog_update();
        core0_alive = false;
        core1_alive = false;
    }
    spin_unlock(wdt_lock, irq);
}
