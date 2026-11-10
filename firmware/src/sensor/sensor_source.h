#pragma once

/*
 * Sensor source abstraction.
 *
 * Defines the interface that heading/rotation estimators implement.
 * main.c selects one at build time via SENSOR_SOURCE_* defines.
 * The control loop (app_control_tick) consumes heading_estimate_t
 * regardless of which sensor produced it.
 *
 * Implementations:
 *   SENSOR_SOURCE_IMU_EKF  3-IMU array + EKF (sensor_imu_ekf.c)
 */

#include <stdbool.h>
#include <stdint.h>
#include "estimation/heading_estimate.h"

typedef struct {
    /* Human-readable name for status prints. */
    const char *name;

    /* Initialize hardware and estimator state.
     * Returns true on success. On failure, main keeps arming disabled. */
    bool (*init)(void);

    /* Produce one heading estimate. dt is seconds since last call.
     * Called at the sensor cadence (typically 1kHz). */
    heading_estimate_t (*tick)(float dt);
} sensor_source_t;
