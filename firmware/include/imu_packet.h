#pragma once

#include <stdint.h>
#include "imu/imu_spi.h"

/* Shared sensor + estimator data passed from core 0 to core 1.
 * Lives in shared memory, protected by spinlock. Holds the raw samples
 * plus the EKF heading estimate core 0 computed from them. */
typedef struct {
    imu_sample_t samples[IMU_COUNT];
    float heading;                /* EKF heading estimate, rad (wrapped) */
    float omega;                  /* EKF angular velocity, rad/s */
    float alpha;                  /* EKF angular acceleration, rad/s^2 */
    uint32_t timestamp_us;
    volatile bool ready;          /* true when new data available */
} imu_packet_t;
