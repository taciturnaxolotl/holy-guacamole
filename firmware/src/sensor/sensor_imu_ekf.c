/*
 * Sensor source: 3-IMU array + EKF.
 * Full PCB with LSM6DSV320X + 2x H3LIS331DL on SPI bus.
 */

#include "sensor/sensor_source.h"

#include <stddef.h>
#include "imu/imu_spi.h"
#include "estimation/ekf.h"
#include "app/control_loop.h"

static ekf_t s_ekf;

/* Expose EKF for auxiliary sensor fusion (e.g., RSSI heading updates). */
ekf_t *sensor_imu_ekf_get_ekf(void) { return &s_ekf; }

static bool imu_ekf_init(void) {
    if (!imu_init()) return false;
    ekf_init(&s_ekf, 0.0f);
    return true;
}

static heading_estimate_t imu_ekf_tick(float dt) {
    imu_sample_t samples[IMU_COUNT];
    if (!imu_read_all(samples)) {
        /* Return stale estimate on read failure; caller handles timeout. */
        heading_estimate_t est;
        est.heading = ekf_heading_wrapped(&s_ekf);
        est.omega = ekf_omega(&s_ekf);
        est.alpha = ekf_alpha(&s_ekf);
        return est;
    }
    return app_sensor_tick(&s_ekf, samples, dt);
}

const sensor_source_t sensor_imu_ekf = {
    .name = "IMU+EKF",
    .init = imu_ekf_init,
    .tick = imu_ekf_tick,
    .feed = NULL,
};
