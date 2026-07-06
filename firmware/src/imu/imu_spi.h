#pragma once

#include <stdint.h>
#include <stdbool.h>

/* IMU identifiers */
#define IMU_A  0  /* LSM6DSV320X, inner, r=12mm */
#define IMU_B  1  /* H3LIS331DL, outer, r=18mm */
#define IMU_C  2  /* H3LIS331DL, outer, r=18mm */
#define IMU_COUNT 3

/* Raw sensor data from one read cycle */
typedef struct {
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
    int16_t gyro_x;   /* only valid for IMU_A (LSM6DSV320X) */
    int16_t gyro_y;
    int16_t gyro_z;
} imu_sample_t;

/* Initialize SPI bus and all three IMUs.
 * Returns true if all sensors respond to WHO_AM_I. */
bool imu_init(void);

/* Read all three IMUs sequentially through the latch.
 * Fills samples[0..2]. Returns true on success.
 * Completes within ~30us at 10MHz SPI. */
bool imu_read_all(imu_sample_t samples[IMU_COUNT]);

/* Read a single IMU by index. Caller manages latch selection. */
bool imu_read_single(uint8_t imu_id, imu_sample_t *sample);
