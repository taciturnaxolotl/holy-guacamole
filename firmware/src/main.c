#include <stdio.h>
#include <string.h>
#include <math.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/sync.h"
#include "hardware/pio.h"

#include "hw_pins.h"
#include "estimation/heading_estimate.h"
#include "dshot/dshot.h"
#include "crsf/crsf.h"
#include "sensor/sensor_dispatch.h"
#include "app/control_loop.h"
#include "safety/watchdog.h"
#include "safety/battery.h"
#include "safety/rc_health.h"
#include "safety/arming.h"
#include "led/head_led.h"
#include "rc_map.h"

#define RAD_TO_DEG 57.2958f
#define STATUS_PRINT_INTERVAL_MS 100
#define CONTROL_LOOP_SLEEP_US 500
#define SENSOR_PERIOD_US 1000   /* 1 kHz sensor cadence on core 0 */

/* Core 1 holds the last estimate between core 0's 1 kHz publishes. If none
 * has arrived for this long the estimate is treated as a sensor fault.
 * 20 ms is 20 missed publishes, far outside scheduling jitter, so a healthy
 * robot never trips it. At 4000 rpm it is about 1.3 revolutions on a frozen
 * heading: translation is wrong for that long, but the motors are cut 100x
 * sooner than the 2 s watchdog would cut them if core 0 hung. */
#define EST_STALE_TIMEOUT_US 20000

/* ---- Shared estimate (core 0 → core 1) ---- */

typedef struct {
    heading_estimate_t est;
    uint64_t timestamp_us;   /* 64-bit: age checks must survive the 71.6 min wrap */
    volatile bool ready;
} shared_estimate_t;

static shared_estimate_t shared_est;
static spin_lock_t *est_lock;
static app_config_t app_cfg;
static volatile bool sensor_ok;

static head_led_status_t led_status(const crsf_state_t *rc, bool link_ok,
                                    bool est_ok, bool armed) {
    if (!sensor_ok || !est_ok) return HEAD_LED_IMU_FAULT;
    /* rc->valid latches on the first good frame, so a dead link after
     * that is a failsafe rather than "never connected". */
    if (!link_ok) return rc->valid ? HEAD_LED_FAILSAFE : HEAD_LED_NO_LINK;
    /* A latched halt keeps the low-battery code up even after the resting
     * pack has climbed back over the warning level. */
    if (battery_low() || !battery_ok()) return HEAD_LED_LOW_BATTERY;
    return armed ? HEAD_LED_ARMED : HEAD_LED_DISARMED;
}

/* ---- Core 1: Control (DSHOT + CRSF) ---- */

static void core1_control_loop(void) {
    if (!dshot_load_program(pio0)) printf("DSHOT PIO program load failed\n");

    dshot_esc_t esc1, esc2;
    if (!dshot_init(&esc1, pio0, PIN_DSHOT1)) printf("DSHOT1 init failed\n");
    if (!dshot_init(&esc2, pio0, PIN_DSHOT2)) printf("DSHOT2 init failed\n");

    crsf_init();
    rc_health_init();
    head_led_init();
    crsf_state_t rc = {0};

    arming_t arming;
    arming_init(&arming);

    /* Core 0 publishes at 1 kHz and this loop runs at about 2 kHz, so most
     * iterations see no new estimate. Hold the last one across iterations
     * and track its age instead of running those ticks on zeros. */
    heading_estimate_t est = {0};
    uint64_t est_us = 0;
    bool est_seen = false;

    printf("Core 1 ready [%s]. Waiting for RC link...\n", sensor_primary.name);

    uint32_t c1_last_us = time_us_32();

    while (1) {
        crsf_poll(&rc);
        /* Sampled after the poll so a frame is never stamped later than now. */
        uint32_t now = to_ms_since_boot(get_absolute_time());
        rc_health_update(rc.valid, rc.last_frame_ms, now);
        bool link_ok = rc_health_ok();

        /* Read latest estimate from core 0. */
        bool est_new = false;
        uint32_t irq = spin_lock_blocking(est_lock);
        if (shared_est.ready) {
            est = shared_est.est;
            est_us = shared_est.timestamp_us;
            shared_est.ready = false;
            est_new = true;
        }
        spin_unlock(est_lock, irq);
        if (est_new) {
            est_seen = true;
            head_led_on_estimate(&est, time_us_32());
        }
        bool est_ok = est_seen && (time_us_64() - est_us) < EST_STALE_TIMEOUT_US;

        /* A switch position only means something on a live link: with no
         * frames the channels read 0, which looks like a low switch. */
        uint16_t arm_ch = rc.channels[RC_CH_ARM];
        bool arm_low = link_ok && arm_ch < RC_SW_LOW;
        bool arm_high = link_ok && rc_switch_high(arm_ch);

        battery_update(now, arm_low);

        bool healthy = sensor_ok && est_ok && link_ok && battery_ok();

        app_command_t cmd = {0};
        cmd.armed = arming_update(&arming, healthy, arm_low, arm_high);
        cmd.mode = rc_mode(rc.channels[RC_CH_MODE]);
        cmd.attack = rc_switch_high(rc.channels[RC_CH_ATTACK]);
        cmd.speed = RC_SPEED_ARMED;   /* no throttle stick: preset spin power */
        /* DRIFT mode actually translates; STOP/SPIN do not. */
        app_cfg.drift_enabled = (cmd.mode == DRIVE_MODE_DRIFT);
        if (cmd.armed) {
            /* Translation is the right stick (X=left/right, Y=fwd/back). */
            cmd.stick_x = (float)((int16_t)rc.channels[RC_CH_STICK_X] - CRSF_CH_MID) /
                          (float)(CRSF_CH_MAX - CRSF_CH_MID);
            cmd.stick_y = (float)((int16_t)rc.channels[RC_CH_STICK_Y] - CRSF_CH_MID) /
                          (float)(CRSF_CH_MAX - CRSF_CH_MID);
        }

        uint32_t c1_now_us = time_us_32();
        float c1_dt = (float)(c1_now_us - c1_last_us) * 1e-6f;
        c1_last_us = c1_now_us;

        /* Left stick X nudges the heading reference ("front"), matching the
         * sim. Heading isn't absolutely observable, so this is a live trim.
         * Only on a live link: before the first frame the channels are 0,
         * which reads as a hard stick deflection, and after a failsafe they
         * hold whatever the stick was doing when the link dropped. */
        float trim_in = (float)((int16_t)rc.channels[RC_CH_TRIM] - CRSF_CH_MID) /
                        (float)(CRSF_CH_MAX - CRSF_CH_MID);
        if (link_ok && fabsf(trim_in) > 0.15f)
            app_cfg.heading_trim -= trim_in * 2.0f * c1_dt;

        app_motors_t m = app_control_tick(&app_cfg, &cmd, &est, c1_dt);

        dshot_set_throttle(&esc1, m.throttle_a);
        dshot_set_throttle(&esc2, m.throttle_b);

        dshot_read_telemetry(&esc1);
        dshot_read_telemetry(&esc2);

        static uint32_t last_print = 0;
        if (now - last_print > STATUS_PRINT_INTERVAL_MS) {
            last_print = now;
            printf("hdg=%6.1f° w=%7.1f RPM=%lu/%lu a/b=%.2f/%.2f %s %s%s%s%s%s\n",
                   (double)(est.heading * RAD_TO_DEG), (double)est.omega,
                   (unsigned long)esc1.telemetry.rpm,
                   (unsigned long)esc2.telemetry.rpm,
                   (double)m.throttle_a, (double)m.throttle_b,
                   link_ok ? "LINK" : "NO-LINK",
                   cmd.armed ? "ARMED" : "DISARMED",
                   battery_low() ? " LOW-BAT" : "",
                   !battery_ok() ? " BAT-HALT" : "",
                   !sensor_ok ? " IMU-FAULT" : "",
                   (sensor_ok && !est_ok) ? " EST-STALE" : "");
        }

        head_led_set_status(led_status(&rc, link_ok, est_ok, cmd.armed));
        head_led_tick(time_us_32());

        watchdog_feed_core1();
        sleep_us(CONTROL_LOOP_SLEEP_US);
    }
}

/* ---- Core 0: Sensor acquisition (main) ---- */

int main(void) {
    stdio_init_all();
    printf("Holy Guacamole firmware starting [%s]...\n", sensor_primary.name);

    app_config_default(&app_cfg);

    int lock_num = spin_lock_claim_unused(true);
    est_lock = spin_lock_instance(lock_num);

    battery_init();

    /* On failure keep running with arming locked out, so core 1 can
     * blink the IMU-fault code instead of the board going dark. */
    sensor_ok = sensor_primary.init();
    if (!sensor_ok) printf("%s init failed, arming disabled\n", sensor_primary.name);

    watchdog_start(2000);
    multicore_launch_core1(core1_control_loop);

    uint64_t last_us = time_us_64();

    while (1) {
        /* Everything here is 64-bit time. A 32-bit microsecond count handed
         * to busy_wait_until() is zero-extended into a deadline that is
         * always in the past once the clock passes 2^32 us (71.6 min), and
         * the loop then free-runs. */
        absolute_time_t tick_start = get_absolute_time();
        uint64_t t = to_us_since_boot(tick_start);
        float dt = (float)(t - last_us) * 1e-6f;
        last_us = t;

        /* HOOK(imu-health): every ~250 ms, if (!imu_health_check()) sensor_ok = false; */

        if (sensor_ok) {
            heading_estimate_t est = sensor_primary.tick(dt);

            uint32_t irq = spin_lock_blocking(est_lock);
            shared_est.est = est;
            shared_est.timestamp_us = t;
            shared_est.ready = true;
            spin_unlock(est_lock, irq);
        }

        battery_sample();
        watchdog_feed();
        busy_wait_until(delayed_by_us(tick_start, SENSOR_PERIOD_US));
    }
}
