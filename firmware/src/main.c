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
#include "led/head_led.h"
#include "rc_map.h"

#define RAD_TO_DEG 57.2958f
#define CRSF_LINK_TIMEOUT_MS 500
#define STATUS_PRINT_INTERVAL_MS 100
#define CONTROL_LOOP_SLEEP_US 500

/* ---- Shared estimate (core 0 → core 1) ---- */

typedef struct {
    heading_estimate_t est;
    uint32_t timestamp_us;
    volatile bool ready;
} shared_estimate_t;

static shared_estimate_t shared_est;
static spin_lock_t *est_lock;
static app_config_t app_cfg;

static bool is_safe_to_arm(const crsf_state_t *rc) {
    return crsf_link_alive(rc, CRSF_LINK_TIMEOUT_MS)
        && rc_health_ok()
        && battery_ok()
        && rc_switch_high(rc->channels[RC_CH_ARM]);
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

    printf("Core 1 ready [%s]. Waiting for RC link...\n", sensor_primary.name);

    uint32_t c1_last_us = time_us_32();

    while (1) {
        crsf_poll(&rc);
        rc_health_update(rc.channels);

        /* Read latest estimate from core 0. */
        heading_estimate_t est = {0};
        uint32_t irq = spin_lock_blocking(est_lock);
        if (shared_est.ready) {
            est = shared_est.est;
            shared_est.ready = false;
            head_led_on_estimate(&est, time_us_32());
        }
        spin_unlock(est_lock, irq);

        app_command_t cmd = {0};
        cmd.armed = is_safe_to_arm(&rc);
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
         * sim. Heading isn't absolutely observable, so this is a live trim. */
        float trim_in = (float)((int16_t)rc.channels[RC_CH_TRIM] - CRSF_CH_MID) /
                        (float)(CRSF_CH_MAX - CRSF_CH_MID);
        if (fabsf(trim_in) > 0.15f)
            app_cfg.heading_trim -= trim_in * 2.0f * c1_dt;

        app_motors_t m = app_control_tick(&app_cfg, &cmd, &est, c1_dt);

        dshot_set_throttle(&esc1, m.throttle_a);
        dshot_set_throttle(&esc2, m.throttle_b);

        dshot_read_telemetry(&esc1);
        dshot_read_telemetry(&esc2);

        static uint32_t last_print = 0;
        uint32_t now = to_ms_since_boot(get_absolute_time());
        if (now - last_print > STATUS_PRINT_INTERVAL_MS) {
            last_print = now;
            printf("hdg=%6.1f° w=%7.1f RPM=%lu/%lu a/b=%.2f/%.2f %s%s%s\n",
                   (double)(est.heading * RAD_TO_DEG), (double)est.omega,
                   (unsigned long)esc1.telemetry.rpm,
                   (unsigned long)esc2.telemetry.rpm,
                   (double)m.throttle_a, (double)m.throttle_b,
                   cmd.armed ? "LINK" : "NO-LINK",
                   battery_low() ? " LOW-BAT" : "",
                   !rc_health_ok() ? " STALE-RC" : "");
        }

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

    /* Primary sensor must init first (owns EKF in fusion mode). */
    if (!sensor_primary.init()) {
        printf("%s init failed\n", sensor_primary.name);
        while (1) tight_loop_contents();
    }

    /* Auxiliary sensor (e.g., RSSI fusion into IMU EKF). */
    if (sensor_aux) {
        if (!sensor_aux->init())
            printf("%s aux init failed (continuing without)\n", sensor_aux->name);
        else
            printf("Aux sensor: %s\n", sensor_aux->name);
    }

    watchdog_start(2000);
    multicore_launch_core1(core1_control_loop);

    uint32_t last_us = time_us_32();

    while (1) {
        uint32_t t = time_us_32();
        float dt = (float)(t - last_us) * 1e-6f;
        last_us = t;

        heading_estimate_t est = sensor_primary.tick(dt);

        uint32_t irq = spin_lock_blocking(est_lock);
        shared_est.est = est;
        shared_est.timestamp_us = t;
        shared_est.ready = true;
        spin_unlock(est_lock, irq);

        battery_sample();
        watchdog_feed();
        busy_wait_until(t + 1000);  /* 1kHz sensor cadence */
    }
}
