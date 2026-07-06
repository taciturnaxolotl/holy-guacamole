#pragma once

#include <stdint.h>
#include "imu/imu_spi.h"

/* Shared sensor data packet passed from core 0 to core 1.
 * Lives in shared memory, protected by spinlock. Reuses the driver's
 * imu_sample_t directly so no field reshaping is needed. */
typedef struct {
    imu_sample_t samples[IMU_COUNT];
    uint32_t timestamp_us;
    volatile bool ready;          /* true when new data available */
} imu_packet_t;
