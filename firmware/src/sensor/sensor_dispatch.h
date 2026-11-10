#pragma once

/*
 * Sensor source dispatch.
 *
 * Each sensor implementation declares its own const sensor_source_t.
 * This header aliases the build-selected one as sensor_primary.
 */

#include "sensor/sensor_source.h"

#if defined(SENSOR_SOURCE_IMU_EKF)
extern const sensor_source_t sensor_imu_ekf;
#define sensor_primary sensor_imu_ekf
#else
#error "Define SENSOR_SOURCE_IMU_EKF (CMakeLists.txt sets it)"
#endif
