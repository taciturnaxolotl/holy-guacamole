#pragma once

/*
 * Sensor source dispatch.
 *
 * Each sensor implementation declares its own const sensor_source_t.
 * This header aliases the build-selected configuration.
 *
 * Supports single-source or dual-source (fusion) modes:
 *   -DSENSOR_SOURCE=imu_ekf          → IMU only
 *   -DSENSOR_SOURCE=rssi             → RSSI only
 *   -DSENSOR_SOURCE=imu_ekf,rssi     → IMU primary + RSSI heading fusion
 */

#include "sensor/sensor_source.h"

/* ── Primary sensor (always present) ──────────────────────────────── */

#if defined(SENSOR_SOURCE_IMU_EKF)
extern const sensor_source_t sensor_imu_ekf;
#define sensor_primary sensor_imu_ekf
#elif defined(SENSOR_SOURCE_RSSI)
extern const sensor_source_t sensor_rssi;
#define sensor_primary sensor_rssi
#else
#error "Define SENSOR_SOURCE_IMU_EKF and/or SENSOR_SOURCE_RSSI via CMake -DSENSOR_SOURCE="
#endif

/* ── Auxiliary sensor (optional, for fusion) ──────────────────────── */

#if defined(SENSOR_SOURCE_IMU_EKF) && defined(SENSOR_SOURCE_RSSI)
extern const sensor_source_t sensor_rssi;
#define sensor_aux (&sensor_rssi)
#else
#define sensor_aux ((const sensor_source_t *)0)
#endif
