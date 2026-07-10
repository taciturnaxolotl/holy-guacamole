#include "test_assert.h"
#include "estimation/accel_cal.h"
#include "estimation/meas_model.h"
#include "estimation/imu_geom.h"

/* Empty tables are a transparent no-op (factor 1.0) for every IMU. */
static void test_empty_is_identity(void) {
    accel_cal_clear();
    for (int imu = 0; imu < ACCEL_CAL_IMUS; imu++) {
        ASSERT_NEAR(accel_cal_get(imu, 0.0f), 1.0f, 1e-6f);
        ASSERT_NEAR(accel_cal_get(imu, 350.0f), 1.0f, 1e-6f);
    }
}

/* Points are stored sorted regardless of insertion order, and the lookup
 * interpolates between them and clamps to the endpoints outside the range. */
static void test_interpolation(void) {
    accel_cal_clear();
    ASSERT_TRUE(accel_cal_add(ACCEL_CAL_IMU_B, 400.0f, 1.05f));  /* out of order */
    ASSERT_TRUE(accel_cal_add(ACCEL_CAL_IMU_B, 0.0f, 1.00f));
    ASSERT_TRUE(accel_cal_add(ACCEL_CAL_IMU_B, 200.0f, 1.02f));
    ASSERT_TRUE(accel_cal_count(ACCEL_CAL_IMU_B) == 3);

    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, 0.0f), 1.00f, 1e-6f);
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, 400.0f), 1.05f, 1e-6f);
    /* Midpoint of [200,400] -> halfway between 1.02 and 1.05. */
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, 300.0f), 1.035f, 1e-5f);
    /* Below/above range clamps to nearest endpoint factor. */
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, -50.0f), 1.00f, 1e-6f);
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, 999.0f), 1.05f, 1e-6f);
}

/* Each IMU keeps its own independent curve. */
static void test_per_imu_independence(void) {
    accel_cal_clear();
    accel_cal_add(ACCEL_CAL_IMU_B, 0.0f, 1.10f);
    accel_cal_add(ACCEL_CAL_IMU_B, 400.0f, 1.10f);
    accel_cal_add(ACCEL_CAL_IMU_C, 0.0f, 0.90f);
    accel_cal_add(ACCEL_CAL_IMU_C, 400.0f, 0.90f);

    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_B, 200.0f), 1.10f, 1e-6f);
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_C, 200.0f), 0.90f, 1e-6f);
    /* IMU-A was never populated -> identity. */
    ASSERT_NEAR(accel_cal_get(ACCEL_CAL_IMU_A, 200.0f), 1.00f, 1e-6f);
    accel_cal_clear();
}

/* accel_cal_apply corrects each IMU's channels with its own curve, leaves
 * an uncalibrated IMU and the gyro untouched, and preserves sign. */
static void test_apply_per_imu(void) {
    accel_cal_clear();
    accel_cal_add(ACCEL_CAL_IMU_B, 0.0f, 1.10f);   /* B: +10% */
    accel_cal_add(ACCEL_CAL_IMU_B, 400.0f, 1.10f);
    accel_cal_add(ACCEL_CAL_IMU_C, 0.0f, 1.20f);   /* C: +20% */
    accel_cal_add(ACCEL_CAL_IMU_C, 400.0f, 1.20f);

    mat_t z;
    mat_zero(&z, MEAS_DIM, 1);
    float base = 100.0f * G_TO_MS2;
    mat_set(&z, MEAS_A_RADIAL, 0, base);       /* IMU-A uncalibrated */
    mat_set(&z, MEAS_A_GYRO, 0, 42.0f);
    mat_set(&z, MEAS_B_RADIAL, 0, base);
    mat_set(&z, MEAS_C_RADIAL, 0, base);
    mat_set(&z, MEAS_C_TANGENTIAL, 0, -base);  /* sign check */

    accel_cal_apply(&z);

    ASSERT_NEAR(mat_get(&z, MEAS_A_RADIAL, 0), base, 1e-3f);       /* untouched */
    ASSERT_NEAR(mat_get(&z, MEAS_A_GYRO, 0), 42.0f, 1e-6f);        /* gyro untouched */
    ASSERT_NEAR(mat_get(&z, MEAS_B_RADIAL, 0), base * 1.10f, 1e-2f);
    ASSERT_NEAR(mat_get(&z, MEAS_C_RADIAL, 0), base * 1.20f, 1e-2f);
    ASSERT_NEAR(mat_get(&z, MEAS_C_TANGENTIAL, 0), -base * 1.20f, 1e-2f);

    accel_cal_clear();
}

int main(void) {
    RUN_TEST(test_empty_is_identity);
    RUN_TEST(test_interpolation);
    RUN_TEST(test_per_imu_independence);
    RUN_TEST(test_apply_per_imu);
    return test_report();
}
