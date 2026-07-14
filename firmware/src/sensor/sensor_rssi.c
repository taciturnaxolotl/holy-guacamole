/*
 * Sensor source: ESP-NOW RSSI edge PLL.
 * Protoboard / no-IMU mode, or auxiliary fusion with IMU+EKF.
 * Based on Trevor Gower's rotation_sensing project:
 *   https://github.com/TGower/rotation_sensing
 */

#include "sensor/sensor_source.h"

#include <stddef.h>
#include "estimation/rssi_heading.h"
#include "estimation/ekf.h"

static rssi_heading_t s_rssi;

/* In standalone mode, RSSI owns its own EKF. In fusion mode, this
 * points to the IMU source's EKF via sensor_imu_ekf_get_ekf(). */
static ekf_t s_standalone_ekf;
static ekf_t *s_ekf = &s_standalone_ekf;

#define R_THETA_PLL 0.03f

static bool rssi_init(void) {
    rssi_heading_init(&s_rssi);

#if defined(SENSOR_SOURCE_IMU_EKF)
    /* Fusion mode: get EKF from IMU source. It must be initialized first. */
    extern ekf_t *sensor_imu_ekf_get_ekf(void);
    s_ekf = sensor_imu_ekf_get_ekf();
#else
    /* Standalone mode: own EKF. */
    ekf_init(&s_standalone_ekf, 0.0f);
#endif

    return true;
}

static heading_estimate_t rssi_tick(float dt) {
    rssi_estimate_t est = rssi_heading_estimate(&s_rssi);

    if (est.locked)
        ekf_update_heading(s_ekf, est.theta, R_THETA_PLL);

    ekf_predict(s_ekf, dt);

    heading_estimate_t out;
    out.heading = ekf_heading_wrapped(s_ekf);
    out.omega = ekf_omega(s_ekf);
    out.alpha = ekf_alpha(s_ekf);
    return out;
}

static void rssi_feed(int8_t rssi, int64_t ts_us) {
    rssi_heading_push(&s_rssi, rssi, ts_us);
}

const sensor_source_t sensor_rssi = {
    .name = "RSSI+PLL",
    .init = rssi_init,
    .tick = rssi_tick,
    .feed = rssi_feed,
};
