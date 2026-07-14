#pragma once

/*
 * Sensor source abstraction.
 *
 * Defines the interface that all heading/rotation estimators implement.
 * main.c selects one at build time via SENSOR_SOURCE_* defines.
 * The control loop (app_control_tick) consumes heading_estimate_t
 * regardless of which sensor produced it.
 *
 * Implementations:
 *   SENSOR_SOURCE_IMU_EKF  — 3-IMU array + EKF (full PCB)
 *   SENSOR_SOURCE_RSSI     — ESP-NOW RSSI edge PLL (protoboard / no IMU)
 */

#include <stdbool.h>
#include <stdint.h>
#include "estimation/heading_estimate.h"

typedef struct {
    /* Human-readable name for status prints. */
    const char *name;

    /* Initialize hardware and estimator state.
     * Returns true on success. On failure, main enters safe halt. */
    bool (*init)(void);

    /* Produce one heading estimate. dt is seconds since last call.
     * Called at the sensor cadence (typically 1kHz). */
    heading_estimate_t (*tick)(float dt);

    /* Optional: feed auxiliary data (e.g., raw RSSI from UART).
     * NULL if the source doesn't need external input. */
    void (*feed)(int8_t value, int64_t timestamp_us);
} sensor_source_t;

/* Implementations declare their own named constants:
 *   sensor_imu_ekf  (in sensor_imu_ekf.c)
 *   sensor_rssi     (in sensor_rssi.c)
 * Use sensor_dispatch.h to get the build-selected one as `sensor_source`. */
