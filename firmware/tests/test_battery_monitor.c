/*
 * Battery decision logic (safety/battery_monitor.h): warning hysteresis,
 * halt persistence, halt latch.
 */

#include "test_assert.h"

#include "safety/battery_monitor.h"

/* Hold one cell voltage for `ms` one-millisecond ticks. */
static void hold(battery_monitor_t *m, uint32_t *now_ms, uint32_t ms,
                 float cell_v, bool disarm_cmd) {
    for (uint32_t i = 0; i < ms; i++) {
        (*now_ms)++;
        battery_monitor_update(m, cell_v, *now_ms, disarm_cmd);
    }
}

static void test_fresh_pack_is_ok(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, 5000, 4.20f, false);
    ASSERT_TRUE(battery_monitor_ok(&m));
    ASSERT_TRUE(!battery_monitor_low(&m));
}

static void test_warning_hysteresis(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);

    hold(&m, &now, 10, BATTERY_WARN_V + 0.01f, false);
    ASSERT_TRUE(!battery_monitor_low(&m));

    hold(&m, &now, 1, BATTERY_WARN_V - 0.01f, false);
    ASSERT_TRUE(battery_monitor_low(&m));

    /* Back over the threshold but inside the hysteresis band: stays set. */
    hold(&m, &now, 1000, BATTERY_WARN_V + 0.01f, false);
    ASSERT_TRUE(battery_monitor_low(&m));
    hold(&m, &now, 1000, BATTERY_WARN_V + BATTERY_HYST_V - 0.01f, false);
    ASSERT_TRUE(battery_monitor_low(&m));

    hold(&m, &now, 1, BATTERY_WARN_V + BATTERY_HYST_V + 0.01f, false);
    ASSERT_TRUE(!battery_monitor_low(&m));

    /* The warning never touches the halt. */
    ASSERT_TRUE(battery_monitor_ok(&m));
}

/* A reading chattering across the warning level must not flicker the flag. */
static void test_warning_does_not_chatter(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, 1, BATTERY_WARN_V - 0.005f, false);
    int clears = 0;
    for (int i = 0; i < 1000; i++) {
        float v = BATTERY_WARN_V + ((i & 1) ? 0.005f : -0.005f);
        hold(&m, &now, 1, v, false);
        if (!battery_monitor_low(&m)) clears++;
    }
    ASSERT_TRUE(clears == 0);
}

/* The case the persistence exists for: spin-up sag on a healthy pack. */
static void test_short_sag_does_not_halt(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, 100, 4.00f, false);
    hold(&m, &now, BATTERY_HALT_PERSIST_MS - 1, 3.30f, false);
    ASSERT_TRUE(battery_monitor_ok(&m));
    hold(&m, &now, 100, 3.90f, false);
    ASSERT_TRUE(battery_monitor_ok(&m));
}

static void test_sustained_low_halts(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, 100, 4.00f, false);
    /* First low tick starts the clock, so the halt lands PERSIST ms later. */
    hold(&m, &now, BATTERY_HALT_PERSIST_MS, BATTERY_HALT_V - 0.01f, false);
    ASSERT_TRUE(battery_monitor_ok(&m));
    hold(&m, &now, 1, BATTERY_HALT_V - 0.01f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));
    ASSERT_TRUE(battery_monitor_low(&m));
}

/* Exactly at the halt level is not below it. */
static void test_at_threshold_is_not_low(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, 10000, BATTERY_HALT_V, false);
    ASSERT_TRUE(battery_monitor_ok(&m));
}

/* Any reading back at the halt level restarts the persistence clock, so
 * repeated short sags never add up to a halt. */
static void test_recovery_restarts_the_clock(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    for (int i = 0; i < 10; i++) {
        hold(&m, &now, BATTERY_HALT_PERSIST_MS - 10, 3.40f, false);
        hold(&m, &now, 1, 3.70f, false);
    }
    ASSERT_TRUE(battery_monitor_ok(&m));
}

static void test_halt_latches_without_disarm(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, BATTERY_HALT_PERSIST_MS + 5, 3.40f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));

    /* Load gone, pack bounces all the way back: still halted. */
    hold(&m, &now, 60000, 4.20f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));
}

static void test_disarm_releases_only_a_recovered_pack(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, BATTERY_HALT_PERSIST_MS + 5, 3.40f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));

    /* Disarm with the pack still under the halt level. */
    hold(&m, &now, 1000, 3.50f, true);
    ASSERT_TRUE(!battery_monitor_ok(&m));

    /* Over the halt level but inside the hysteresis band. */
    hold(&m, &now, 1000, BATTERY_HALT_V + BATTERY_HYST_V - 0.01f, true);
    ASSERT_TRUE(!battery_monitor_ok(&m));

    /* Recovered, but nobody is commanding a disarm. */
    hold(&m, &now, 1000, BATTERY_HALT_V + BATTERY_HYST_V + 0.01f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));

    /* Recovered and disarmed. */
    hold(&m, &now, 1, BATTERY_HALT_V + BATTERY_HYST_V + 0.01f, true);
    ASSERT_TRUE(battery_monitor_ok(&m));
}

/* Disarmed the whole time: a flat pack still halts, and stays halted. */
static void test_flat_pack_halts_while_disarmed(void) {
    battery_monitor_t m;
    uint32_t now = 0;
    battery_monitor_init(&m);
    hold(&m, &now, BATTERY_HALT_PERSIST_MS + 5, 3.20f, true);
    ASSERT_TRUE(!battery_monitor_ok(&m));
    hold(&m, &now, 5000, 3.20f, true);
    ASSERT_TRUE(!battery_monitor_ok(&m));
}

/* The persistence timer must survive the 32-bit millisecond wrap. */
static void test_persistence_across_ms_wrap(void) {
    battery_monitor_t m;
    uint32_t now = 0xFFFFFFFFu - 700u;
    battery_monitor_init(&m);
    hold(&m, &now, BATTERY_HALT_PERSIST_MS, 3.40f, false);
    ASSERT_TRUE(now < 2000u);               /* wrapped */
    ASSERT_TRUE(battery_monitor_ok(&m));
    hold(&m, &now, 1, 3.40f, false);
    ASSERT_TRUE(!battery_monitor_ok(&m));
}

int main(void) {
    RUN_TEST(test_fresh_pack_is_ok);
    RUN_TEST(test_warning_hysteresis);
    RUN_TEST(test_warning_does_not_chatter);
    RUN_TEST(test_short_sag_does_not_halt);
    RUN_TEST(test_sustained_low_halts);
    RUN_TEST(test_at_threshold_is_not_low);
    RUN_TEST(test_recovery_restarts_the_clock);
    RUN_TEST(test_halt_latches_without_disarm);
    RUN_TEST(test_disarm_releases_only_a_recovered_pack);
    RUN_TEST(test_flat_pack_halts_while_disarmed);
    RUN_TEST(test_persistence_across_ms_wrap);
    return test_report();
}
