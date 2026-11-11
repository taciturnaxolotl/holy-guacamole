/*
 * RC link health (safety/rc_health.c): the link is healthy while valid
 * channel frames keep arriving, whatever the sticks are doing.
 */

#include "test_assert.h"

#include "safety/rc_health.h"

static void test_no_frame_yet_is_unhealthy(void) {
    rc_health_init();
    ASSERT_TRUE(!rc_health_ok());
    /* Parser state is all zeros before the first frame. */
    for (uint32_t now = 0; now < 5000; now++) {
        rc_health_update(false, 0, now);
        ASSERT_TRUE(!rc_health_ok());
    }
}

static void test_frames_arriving_is_healthy(void) {
    rc_health_init();
    uint32_t last = 0;
    for (uint32_t now = 100; now < 2000; now++) {
        if (now % 4 == 0) last = now;       /* 250 Hz frames */
        rc_health_update(true, last ? last : 100, now);
        ASSERT_TRUE(rc_health_ok());
    }
}

/* The regression this module was rewritten for: frames keep arriving with
 * the sticks perfectly still (identical channel data) for a long time. The
 * old checksum rule called that a failsafe after 3 s. The new interface
 * does not take channel values at all, so a minute of steady frames is the
 * whole test. */
static void test_still_sticks_stay_healthy(void) {
    rc_health_init();
    uint32_t last = 1000;
    for (uint32_t now = 1000; now < 61000; now++) {
        if (now % 4 == 0) last = now;
        rc_health_update(true, last, now);
        ASSERT_TRUE(rc_health_ok());
    }
}

static void test_timeout_boundary(void) {
    rc_health_init();
    rc_health_update(true, 1000, 1000);
    ASSERT_TRUE(rc_health_ok());
    rc_health_update(true, 1000, 1000 + RC_LINK_TIMEOUT_MS - 1);
    ASSERT_TRUE(rc_health_ok());
    rc_health_update(true, 1000, 1000 + RC_LINK_TIMEOUT_MS);
    ASSERT_TRUE(!rc_health_ok());
}

static void test_loss_then_new_frame_recovers(void) {
    rc_health_init();
    rc_health_update(true, 1000, 1000);
    rc_health_update(true, 1000, 3000);
    ASSERT_TRUE(!rc_health_ok());
    rc_health_update(true, 3001, 3001);
    ASSERT_TRUE(rc_health_ok());
}

/* A burst of dropped frames shorter than the timeout is not a loss. */
static void test_short_gap_is_tolerated(void) {
    rc_health_init();
    rc_health_update(true, 1000, 1000);
    for (uint32_t now = 1000; now < 1000 + RC_LINK_TIMEOUT_MS; now++) {
        rc_health_update(true, 1000, now);
        ASSERT_TRUE(rc_health_ok());
    }
    rc_health_update(true, 1499, 1500);
    ASSERT_TRUE(rc_health_ok());
}

/* A frame stamped just after `now` was sampled is fresh, not ancient. */
static void test_frame_stamped_after_now(void) {
    rc_health_init();
    rc_health_update(true, 1001, 1000);
    ASSERT_TRUE(rc_health_ok());
}

static void test_healthy_across_ms_wrap(void) {
    rc_health_init();
    uint32_t now = 0xFFFFFFFFu - 100u;
    uint32_t last = now;
    for (int i = 0; i < 300; i++) {
        now++;
        if (i % 4 == 0) last = now;
        rc_health_update(true, last, now);
        ASSERT_TRUE(rc_health_ok());
    }
    ASSERT_TRUE(now < 1000u);               /* wrapped */
}

/* Once lost, the same old frame can never look fresh again, even when the
 * 32-bit age wraps round to a small number (49.7 days of silence). */
static void test_lost_link_stays_lost_across_age_wrap(void) {
    rc_health_init();
    rc_health_update(true, 1000, 1000);
    rc_health_update(true, 1000, 1000 + RC_LINK_TIMEOUT_MS);
    ASSERT_TRUE(!rc_health_ok());
    /* now has gone all the way round: unsigned age is 10 ms. */
    rc_health_update(true, 1000, 1010);
    ASSERT_TRUE(!rc_health_ok());
    rc_health_update(true, 1000, 999);
    ASSERT_TRUE(!rc_health_ok());
    /* A real new frame still recovers. */
    rc_health_update(true, 1020, 1020);
    ASSERT_TRUE(rc_health_ok());
}

static void test_init_resets(void) {
    rc_health_init();
    rc_health_update(true, 1000, 1000);
    ASSERT_TRUE(rc_health_ok());
    rc_health_init();
    ASSERT_TRUE(!rc_health_ok());
}

int main(void) {
    RUN_TEST(test_no_frame_yet_is_unhealthy);
    RUN_TEST(test_frames_arriving_is_healthy);
    RUN_TEST(test_still_sticks_stay_healthy);
    RUN_TEST(test_timeout_boundary);
    RUN_TEST(test_loss_then_new_frame_recovers);
    RUN_TEST(test_short_gap_is_tolerated);
    RUN_TEST(test_frame_stamped_after_now);
    RUN_TEST(test_healthy_across_ms_wrap);
    RUN_TEST(test_lost_link_stays_lost_across_age_wrap);
    RUN_TEST(test_init_resets);
    return test_report();
}
