/*
 * Arming interlock (safety/arming.h), plus the interlock and the battery
 * monitor wired together the way main.c wires them.
 */

#include "test_assert.h"

#include "safety/arming.h"
#include "safety/battery_monitor.h"

/* Switch positions as main.c reports them. */
#define SW_LOW   true,  false
#define SW_MID   false, false
#define SW_HIGH  false, true

static void test_starts_disarmed(void) {
    arming_t a;
    arming_init(&a);
    ASSERT_TRUE(!arming_is_armed(&a));
    ASSERT_TRUE(a.state == ARMING_LOCKED);
}

/* Boot or watchdog reset with the switch already high. */
static void test_boot_with_switch_high_does_not_arm(void) {
    arming_t a;
    arming_init(&a);
    for (int i = 0; i < 5000; i++) {
        ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
    }
    ASSERT_TRUE(a.state == ARMING_LOCKED);
}

static void test_low_then_high_arms(void) {
    arming_t a;
    arming_init(&a);
    ASSERT_TRUE(!arming_update(&a, true, SW_LOW));
    ASSERT_TRUE(a.state == ARMING_READY);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
    /* Stays armed while the switch is held high. */
    for (int i = 0; i < 100; i++) ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
}

/* A 3-position switch passes through the middle on its way up. */
static void test_low_mid_high_arms(void) {
    arming_t a;
    arming_init(&a);
    ASSERT_TRUE(!arming_update(&a, true, SW_LOW));
    ASSERT_TRUE(!arming_update(&a, true, SW_MID));
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
}

static void test_switch_low_disarms_and_rearms_on_next_edge(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, true, SW_LOW));
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
}

/* Leaving the high stop disarms, and coming back to it without touching the
 * low stop does not re-arm. This is what stops a value jittering around the
 * high threshold from toggling the motors. */
static void test_mid_disarms_and_needs_full_low(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, true, SW_MID));
    ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, true, SW_LOW));
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
}

/* The switch sitting low during a fault must not count as the arming low. */
static void test_low_while_unhealthy_does_not_prime(void) {
    arming_t a;
    arming_init(&a);
    ASSERT_TRUE(!arming_update(&a, false, SW_LOW));
    ASSERT_TRUE(a.state == ARMING_LOCKED);
    ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
}

/* Link loss as main.c presents it: unhealthy, and no switch position. */
static void test_link_loss_disarms_and_recovery_does_not_rearm(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));

    ASSERT_TRUE(!arming_update(&a, false, SW_MID));
    ASSERT_TRUE(a.state == ARMING_LOCKED);

    /* Link back, switch still high where the pilot left it. */
    for (int i = 0; i < 5000; i++) {
        ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
    }

    /* A deliberate new low-to-high move arms again. */
    ASSERT_TRUE(!arming_update(&a, true, SW_LOW));
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
}

/* A fault that arrives after the low but before the high cancels the low. */
static void test_fault_between_low_and_high_cancels(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    arming_update(&a, false, SW_LOW);
    ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
}

/* A one-tick fault (for example one stale estimate) is enough to lock. */
static void test_single_tick_fault_locks(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, false, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, true, SW_HIGH));
}

/* Contradictory inputs must resolve to the safe side. */
static void test_low_and_high_together_is_low(void) {
    arming_t a;
    arming_init(&a);
    arming_update(&a, true, SW_LOW);
    ASSERT_TRUE(arming_update(&a, true, SW_HIGH));
    ASSERT_TRUE(!arming_update(&a, true, true, true));
}

/* ---- Interlock + battery monitor, composed as in main.c's core 1 loop ---- */

typedef struct {
    arming_t arming;
    battery_monitor_t bat;
    uint32_t now_ms;
} rig_t;

static void rig_init(rig_t *r) {
    arming_init(&r->arming);
    battery_monitor_init(&r->bat);
    r->now_ms = 1000;
}

/* Run `ms` one-millisecond control ticks; returns the final armed state. */
static bool rig_run(rig_t *r, uint32_t ms, float cell_v, bool sw_low, bool sw_high) {
    bool armed = arming_is_armed(&r->arming);
    for (uint32_t i = 0; i < ms; i++) {
        r->now_ms++;
        battery_monitor_update(&r->bat, cell_v, r->now_ms, sw_low);
        bool healthy = battery_monitor_ok(&r->bat);
        armed = arming_update(&r->arming, healthy, sw_low, sw_high);
    }
    return armed;
}

static void test_battery_halt_latches_through_interlock(void) {
    rig_t r;
    rig_init(&r);

    ASSERT_TRUE(!rig_run(&r, 10, 4.0f, SW_LOW));
    ASSERT_TRUE(rig_run(&r, 10, 4.0f, SW_HIGH));

    /* Spin-up sag shorter than the persistence window: stays armed. */
    ASSERT_TRUE(rig_run(&r, BATTERY_HALT_PERSIST_MS - 100, 3.40f, SW_HIGH));
    ASSERT_TRUE(rig_run(&r, 500, 3.90f, SW_HIGH));

    /* Sustained low: halts and disarms. */
    ASSERT_TRUE(!rig_run(&r, BATTERY_HALT_PERSIST_MS + 10, 3.40f, SW_HIGH));
    ASSERT_TRUE(!battery_monitor_ok(&r.bat));

    /* Motors off, pack recovers, switch still high: must stay down. */
    ASSERT_TRUE(!rig_run(&r, 5000, 4.00f, SW_HIGH));
    ASSERT_TRUE(!battery_monitor_ok(&r.bat));

    /* Operator disarms: the halt releases but the robot is still disarmed. */
    ASSERT_TRUE(!rig_run(&r, 10, 4.00f, SW_LOW));
    ASSERT_TRUE(battery_monitor_ok(&r.bat));

    /* Deliberate re-arm. */
    ASSERT_TRUE(rig_run(&r, 10, 4.00f, SW_HIGH));
}

/* A pack that is still flat at rest cannot be re-armed by cycling the switch. */
static void test_flat_pack_cannot_rearm(void) {
    rig_t r;
    rig_init(&r);
    rig_run(&r, 10, 4.0f, SW_LOW);
    ASSERT_TRUE(rig_run(&r, 10, 4.0f, SW_HIGH));
    ASSERT_TRUE(!rig_run(&r, BATTERY_HALT_PERSIST_MS + 10, 3.40f, SW_HIGH));

    ASSERT_TRUE(!rig_run(&r, 1000, 3.55f, SW_LOW));
    ASSERT_TRUE(!rig_run(&r, 1000, 3.55f, SW_HIGH));
    ASSERT_TRUE(!battery_monitor_ok(&r.bat));
}

int main(void) {
    RUN_TEST(test_starts_disarmed);
    RUN_TEST(test_boot_with_switch_high_does_not_arm);
    RUN_TEST(test_low_then_high_arms);
    RUN_TEST(test_low_mid_high_arms);
    RUN_TEST(test_switch_low_disarms_and_rearms_on_next_edge);
    RUN_TEST(test_mid_disarms_and_needs_full_low);
    RUN_TEST(test_low_while_unhealthy_does_not_prime);
    RUN_TEST(test_link_loss_disarms_and_recovery_does_not_rearm);
    RUN_TEST(test_fault_between_low_and_high_cancels);
    RUN_TEST(test_single_tick_fault_locks);
    RUN_TEST(test_low_and_high_together_is_low);
    RUN_TEST(test_battery_halt_latches_through_interlock);
    RUN_TEST(test_flat_pack_cannot_rearm);
    return test_report();
}
