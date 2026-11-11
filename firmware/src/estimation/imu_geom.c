#include "imu_geom.h"

#include <math.h>

/* As-placed geometry from docs/spec.md "IMU placement": the nominal
 * 0 / 90 / 210 degree array is rotated 166 degrees CCW on the rev 2 board.
 *   IMU-A (U4): r=12mm, 166deg, LSM6DSV320X (gyro present)
 *   IMU-B (U5): r=18mm, 256deg, H3LIS331DL
 *   IMU-C (U6): r=18mm, 16deg,  H3LIS331DL
 * Replace with measured post-assembly positions during calibration. */
#define DEG ((float)M_PI / 180.0f)

const imu_geom_t imu_geom[IMU_COUNT_GEOM] = {
    { .radius_m = 0.012f, .angle_rad = 166.0f * DEG, .has_gyro = true  },
    { .radius_m = 0.018f, .angle_rad = 256.0f * DEG, .has_gyro = false },
    { .radius_m = 0.018f, .angle_rad = 16.0f  * DEG, .has_gyro = false },
};
