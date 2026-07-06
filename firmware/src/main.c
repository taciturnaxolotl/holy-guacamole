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
#include "imu/latch.h"
#include "crsf/crsf.h"

/* ---- Shared sensor data (core 0 → core 1) ---- */

static imu_packet_t shared_imu;
static spin_lock_t *imu_lock;

/* ---- Core 1: Control (owns DSHOT + CRSF) ---- */

static void core1_control_loop(void) {
    /* Core 1 owns the PIO (DSHOT) and UART0 (CRSF) peripherals. */
    if (!dshot_load_program(pio0)) {
        printf("DSHOT PIO program load failed\n");
    }

    dshot_esc_t esc1, esc2;
    if (!dshot_init(&esc1, pio0, PIN_DSHOT1)) printf("DSHOT1 init failed\n");
    if (!dshot_init(&esc2, pio0, PIN_DSHOT2)) printf("DSHOT2 init failed\n");

    crsf_init();
    crsf_state_t rc = {0};

    printf("Core 1 ready. Waiting for RC link...\n");

    while (1) {
        crsf_poll(&rc);

        /* Read latest IMU data published by core 0 */
        imu_packet_t imu_snapshot;
        uint32_t irq = spin_lock_blocking(imu_lock);
        imu_snapshot = shared_imu;
        shared_imu.ready = false;
        spin_unlock(imu_lock, irq);

        /* Map throttle stick (channel 2, 0-indexed) to [0.0, 1.0] */
        float throttle = 0.0f;
        if (crsf_link_alive(&rc, 500)) {
            int16_t raw = (int16_t)rc.channels[2];
            if (raw > CRSF_CH_MIN) {
                throttle = (float)(raw - CRSF_CH_MIN) / (float)(CRSF_CH_MAX - CRSF_CH_MIN);
                if (throttle > 1.0f) throttle = 1.0f;
            }
        }

        dshot_set_throttle(&esc1, throttle);
        dshot_set_throttle(&esc2, throttle);

        dshot_read_telemetry(&esc1);
        dshot_read_telemetry(&esc2);

        /* Periodic status print (every ~100ms) */
        static uint32_t last_print = 0;
        uint32_t now = to_ms_since_boot(get_absolute_time());
        if (now - last_print > 100) {
            last_print = now;
            printf("RPM: %lu/%lu  Ch[0]:%u Ch[1]:%u Ch[2]:%u  Link:%s  IMU:%s\n",
                   esc1.telemetry.rpm, esc2.telemetry.rpm,
                   rc.channels[0], rc.channels[1], rc.channels[2],
                   crsf_link_alive(&rc, 500) ? "OK" : "LOST",
                   imu_snapshot.ready ? "new" : "-");
        }

        sleep_us(500);  /* ~2kHz control loop */
    }
}

/* ---- Core 0: Sensor acquisition (main, owns SPI0 + latch) ---- */

int main(void) {
    stdio_init_all();
    printf("Holy Guacamole firmware starting...\n");

    /* Spinlock guarding the shared IMU packet */
    int lock_num = spin_lock_claim_unused(true);
    imu_lock = spin_lock_instance(lock_num);

    /* Core 0 owns the IMU SPI bus and chip-select latch */
    if (!imu_init()) {
        printf("IMU init failed\n");
        while (1) tight_loop_contents();
    }

    /* Hand the control loop to core 1 */
    multicore_launch_core1(core1_control_loop);

    imu_sample_t samples[IMU_COUNT];

    while (1) {
        uint32_t t = time_us_32();

        if (imu_read_all(samples)) {
            /* Publish under spinlock. Packet holds imu_sample_t directly. */
            uint32_t irq = spin_lock_blocking(imu_lock);
            memcpy(shared_imu.samples, samples, sizeof(samples));
            shared_imu.timestamp_us = t;
            shared_imu.ready = true;
            spin_unlock(imu_lock, irq);
        }

        busy_wait_until(t + 1000);  /* 1kHz sensor cadence */
    }
}
