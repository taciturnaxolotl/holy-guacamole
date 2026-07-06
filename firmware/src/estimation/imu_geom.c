#include "imu_geom.h"

#include <math.h>

/* Nominal geometry from the spec:
 *   IMU-A: r=12mm, 0deg,  LSM6DSV320X (gyro present)
 *   IMU-B: r=18mm, 90deg, H3LIS331DL
 *   IMU-C: r=18mm, 210deg, H3LIS331DL
 * Replace with measured post-assembly positions during calibration. */
const imu_geom_t imu_geom[IMU_COUNT_GEOM] = {
    { .radius_m = 0.012f, .angle_rad = 0.0f,                   .has_gyro = true  },
    { .radius_m = 0.018f, .angle_rad = 90.0f  * (float)M_PI / 180.0f, .has_gyro = false },
    { .radius_m = 0.018f, .angle_rad = 210.0f * (float)M_PI / 180.0f, .has_gyro = false },
};
