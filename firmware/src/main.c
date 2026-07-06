#include <stdio.h>
#include <string.h>

#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/sync.h"
#include "hardware/pio.h"

#include "hw_pins.h"
#include "imu_packet.h"
#include "dshot/dshot.h"
#include "imu/imu_spi.h"
#include "crsf/crsf.h"
#include "math/linalg.h"
#include "estimation/ekf.h"
#include "estimation/imu_convert.h"
#include "control/drift.h"

/* Gate the closed-loop drift controller. While 0, motors follow the raw
 * throttle stick (bring-up behaviour) and the EKF/drift outputs are only
 * printed for observation. Flip to 1 only after the heading estimate is
 * validated against the real robot on the bench. */
#define ENABLE_DRIFT_CONTROL 0

/* ---- Shared sensor data (core 0 → core 1) ---- */

static imu_packet_t shared_imu;
static spin_lock_t *imu_lock;

/* ---- Core 1: Control (owns DSHOT + CRSF) ---- */

static void core1_control_loop(void) {
    if (!dshot_load_program(pio0)) printf("DSHOT PIO program load failed\n");

    dshot_esc_t esc1, esc2;
    if (!dshot_init(&esc1, pio0, PIN_DSHOT1)) printf("DSHOT1 init failed\n");
    if (!dshot_init(&esc2, pio0, PIN_DSHOT2)) printf("DSHOT2 init failed\n");

    crsf_init();
    crsf_state_t rc = {0};

    printf("Core 1 ready. Waiting for RC link...\n");

    while (1) {
        crsf_poll(&rc);

        imu_packet_t imu;
        uint32_t irq = spin_lock_blocking(imu_lock);
        imu = shared_imu;
        shared_imu.ready = false;
        spin_unlock(imu_lock, irq);

        /* Stick channels: ch2 throttle/base, ch0/ch1 drift vector. */
        float base = 0.0f;
        float stick_x = 0.0f, stick_y = 0.0f;
        bool armed = crsf_link_alive(&rc, 500);
        if (armed) {
            int16_t thr = (int16_t)rc.channels[2];
            if (thr > CRSF_CH_MIN) {
                base = (float)(thr - CRSF_CH_MIN) / (float)(CRSF_CH_MAX - CRSF_CH_MIN);
                if (base > 1.0f) base = 1.0f;
            }
            stick_x = (float)((int16_t)rc.channels[0] - CRSF_CH_MID) /
                      (float)(CRSF_CH_MAX - CRSF_CH_MID);
            stick_y = (float)((int16_t)rc.channels[1] - CRSF_CH_MID) /
                      (float)(CRSF_CH_MAX - CRSF_CH_MID);
        }

        /* Compute drift modulation from EKF heading (for observation). */
        float authority, phi;
        drift_from_stick(stick_x, stick_y, 0.5f, &authority, &phi);
        drift_throttles_t d = drift_compute(imu.heading, base, authority, phi);

#if ENABLE_DRIFT_CONTROL
        dshot_set_throttle(&esc1, armed ? d.a : 0.0f);
        dshot_set_throttle(&esc2, armed ? d.b : 0.0f);
#else
        /* Bring-up: both motors follow the raw throttle stick. */
        dshot_set_throttle(&esc1, base);
        dshot_set_throttle(&esc2, base);
        (void)d;
#endif

        dshot_read_telemetry(&esc1);
        dshot_read_telemetry(&esc2);

        static uint32_t last_print = 0;
        uint32_t now = to_ms_since_boot(get_absolute_time());
        if (now - last_print > 100) {
            last_print = now;
            printf("hdg=%6.1f deg  w=%7.1f rad/s  RPM=%lu/%lu  drift a/b=%.2f/%.2f  Link:%s\n",
                   (double)(imu.heading * 57.2958f), (double)imu.omega,
                   (unsigned long)esc1.telemetry.rpm,
                   (unsigned long)esc2.telemetry.rpm,
                   (double)d.a, (double)d.b,
                   armed ? "OK" : "LOST");
        }

        sleep_us(500);
    }
}

/* ---- Core 0: Sensor acquisition + EKF (main, owns SPI0 + latch) ---- */

int main(void) {
    stdio_init_all();
    printf("Holy Guacamole firmware starting...\n");

    int lock_num = spin_lock_claim_unused(true);
    imu_lock = spin_lock_instance(lock_num);

    if (!imu_init()) {
        printf("IMU init failed\n");
        while (1) tight_loop_contents();
    }

    ekf_t ekf;
    ekf_init(&ekf, 0.0f);

    multicore_launch_core1(core1_control_loop);

    imu_sample_t samples[IMU_COUNT];
    uint32_t last_us = time_us_32();

    while (1) {
        uint32_t t = time_us_32();

        if (imu_read_all(samples)) {
            float dt = (float)(t - last_us) * 1e-6f;
            last_us = t;
            if (dt <= 0.0f || dt > 0.1f) dt = 0.001f;  /* guard bad deltas */

            mat_t z;
            imu_samples_to_meas(samples, &z);
            ekf_predict(&ekf, dt);
            ekf_update(&ekf, &z);

            uint32_t irq = spin_lock_blocking(imu_lock);
            memcpy(shared_imu.samples, samples, sizeof(samples));
            shared_imu.heading = ekf_heading_wrapped(&ekf);
            shared_imu.omega = ekf_omega(&ekf);
            shared_imu.alpha = ekf_alpha(&ekf);
            shared_imu.timestamp_us = t;
            shared_imu.ready = true;
            spin_unlock(imu_lock, irq);
        }

        busy_wait_until(t + 1000);  /* 1kHz sensor cadence */
    }
}
