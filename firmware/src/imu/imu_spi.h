#pragma once

#include <stdint.h>
#include <stdbool.h>

/* IMU identifiers */
#define IMU_A  0  /* LSM6DSV320X, inner, r=12mm */
#define IMU_B  1  /* H3LIS331DL, outer, r=18mm */
#define IMU_C  2  /* H3LIS331DL, outer, r=18mm */
#define IMU_COUNT 3

/* Raw sensor data from one read cycle, in each chip's own axes. The
 * chips are not mounted alike: estimation/imu_convert.c holds the
 * per-chip radial/tangential mapping.
 *
 * accel_*: IMU_A reports its high-g channel (+/-320 g, 16-bit); its
 * low-g accelerometer is left off. IMU_B/C report +/-400 g as 12 bits
 * left-justified in the 16-bit word. */
typedef struct {
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
    int16_t gyro_x;   /* only valid for IMU_A (LSM6DSV320X) */
    int16_t gyro_y;
    int16_t gyro_z;
} imu_sample_t;

/* Initialize the SPI bus and the latch, then configure all three IMUs.
 * Returns true only if every sensor answers WHO_AM_I and reads back the
 * configuration that was written. Retries for up to about 50 ms, so a
 * sensor still booting after power-up is not reported missing.
 * Outputs need time to settle after a true return: the gyro turn-on
 * time is 40 ms (ST DS14623 table 4). */
bool imu_init(void);

/* Rewrite the configuration of all three IMUs and verify it, without
 * touching the SPI or GPIO setup. Use it to recover when
 * imu_health_check() fails, for example after a sensor browns out and
 * comes back with its power-on defaults. One attempt, no sleeps, about
 * 110 us of bus time. Returns the same verdict as imu_health_check(). */
bool imu_reinit(void);

/* Read back WHO_AM_I and every configuration register of all three IMUs
 * and compare them with what imu_init() wrote. Returns false on any
 * mismatch. Without it a sensor that reset itself or dropped off the bus
 * keeps feeding wrongly scaled, frozen or all-ones samples to the
 * estimator and nothing notices.
 *
 * About 60 us of bus time, so a few calls per second from the sensor
 * loop are free. Like everything here it drives the shared SPI bus and
 * latch: call it from the same context as imu_read_all(), never
 * concurrently with it. */
bool imu_health_check(void);

/* Read all three IMUs sequentially through the latch.
 * Fills samples[0..2]. Returns true on success.
 * Four SPI transactions (IMU_A needs two, its gyro and high-g outputs
 * are not adjacent registers), about 36 us of bus time at 10 MHz. */
bool imu_read_all(imu_sample_t samples[IMU_COUNT]);
