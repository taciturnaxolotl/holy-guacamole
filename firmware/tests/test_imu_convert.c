#include "test_assert.h"

#include "estimation/imu_convert.h"
#include "estimation/imu_geom.h"
#include "estimation/meas_model.h"

#include <math.h>
#include <string.h>

/*
 * Raw counts -> EKF measurement vector: scale factors and the per-chip
 * axis map.
 *
 * Everything here is worked out independently of imu_convert.c. The
 * sensitivities are datasheet literals, and the axis checks start from
 * where each chip axis points on the board, apply the physics of a
 * spinning rigid body, and require the result to equal meas_predict().
 */

#define DEG ((float)M_PI / 180.0f)

/* ST DS14623 Rev 3 table 3 (LSM6DSV320X) and DS9012 Rev 5 table 2
 * (H3LIS331DL, per 12-bit digit; the digit is 16 counts of the
 * left-justified 16-bit word). */
#define LSM6_HG_MG_PER_LSB       10.417f
#define LSM6_GYRO_MDPS_PER_LSB   140.0f
#define H3LIS_MG_PER_DIGIT       195.0f
#define H3LIS_COUNTS_PER_DIGIT   16.0f

static float g_per_count(int imu) {
    return imu == IMU_A ? LSM6_HG_MG_PER_LSB / 1000.0f
                        : H3LIS_MG_PER_DIGIT / 1000.0f / H3LIS_COUNTS_PER_DIGIT;
}

/* Bearing on the board (degrees CCW from board +x, seen from the
 * component side) of each chip's +X and +Y axis.
 *
 * Footprint rotations in hardware/guac.kicad_pcb: U4 166, U5 166,
 * U6 -164 (= 196). Axes relative to the footprint, from the datasheet
 * drawings and the pad layout:
 *   LSM6DSV320X (DS14623 figure 5): pin 1 top left, +X along the long
 *     edge away from pin 1, +Y toward the pin 12..14 edge. Same frame as
 *     the footprint: X at rot, Y at rot + 90.
 *   H3LIS331DL (DS9012 figure 2): +X leaves through the pin 1..5 edge,
 *     +Y through the pin 6..8 edge. The footprint has pins 1..5 along
 *     its bottom edge and 6..8 up its right edge: X at rot - 90, Y at rot.
 */
static const struct { float x_deg; float y_deg; } chip_axes[IMU_COUNT] = {
    [IMU_A] = { 166.0f, 256.0f },
    [IMU_B] = {  76.0f, 166.0f },
    [IMU_C] = { 106.0f, 196.0f },
};

static int16_t to_counts(float v) {
    float r = roundf(v);
    if (r > 32767.0f) r = 32767.0f;
    if (r < -32768.0f) r = -32768.0f;
    return (int16_t)r;
}

/* What the three chips would report on a body spinning at omega (rad/s,
 * CCW positive) with angular acceleration alpha. An accelerometer reads
 * the acceleration of its own mounting point: omega^2 r toward the
 * centre plus alpha r along the CCW tangent. */
static void spin_samples(float omega, float alpha, imu_sample_t s[IMU_COUNT]) {
    memset(s, 0, sizeof(imu_sample_t) * IMU_COUNT);
    for (int i = 0; i < IMU_COUNT; i++) {
        float phi = imu_geom[i].angle_rad;
        float r = imu_geom[i].radius_m;
        float ax = -omega * omega * r * cosf(phi) - alpha * r * sinf(phi);
        float ay = -omega * omega * r * sinf(phi) + alpha * r * cosf(phi);

        float xb = chip_axes[i].x_deg * DEG;
        float yb = chip_axes[i].y_deg * DEG;
        float per_count = g_per_count(i) * G_TO_MS2;
        s[i].accel_x = to_counts((ax * cosf(xb) + ay * sinf(xb)) / per_count);
        s[i].accel_y = to_counts((ax * cosf(yb) + ay * sinf(yb)) / per_count);
        /* Out-of-plane axis carries gravity, which must not leak in. */
        s[i].accel_z = to_counts(1.0f / g_per_count(i));
    }
    s[IMU_A].gyro_z = to_counts(omega / DEG / (LSM6_GYRO_MDPS_PER_LSB / 1000.0f));
}

static void predict(float omega, float alpha, mat_t *z) {
    mat_t x;
    mat_zero(&x, ST_DIM, 1);
    mat_set(&x, ST_OMEGA, 0, omega);
    mat_set(&x, ST_ALPHA, 0, alpha);
    meas_predict(&x, z);
}

/* ---- geometry the axis table depends on ---- */

static void test_geometry_matches_board(void) {
    ASSERT_NEAR(imu_geom[IMU_A].radius_m, 0.012f, 1e-7f);
    ASSERT_NEAR(imu_geom[IMU_B].radius_m, 0.018f, 1e-7f);
    ASSERT_NEAR(imu_geom[IMU_C].radius_m, 0.018f, 1e-7f);
    ASSERT_NEAR(imu_geom[IMU_A].angle_rad, 166.0f * DEG, 1e-5f);
    ASSERT_NEAR(imu_geom[IMU_B].angle_rad, 256.0f * DEG, 1e-5f);
    ASSERT_NEAR(imu_geom[IMU_C].angle_rad, 16.0f * DEG, 1e-5f);
    ASSERT_TRUE(imu_geom[IMU_A].has_gyro && !imu_geom[IMU_B].has_gyro && !imu_geom[IMU_C].has_gyro);

    /* Board positions listed in docs/spec.md "IMU placement" (mm). */
    static const float xy_mm[IMU_COUNT][2] = {
        { -11.64f, 2.90f }, { -4.35f, -17.47f }, { 17.30f, 4.96f },
    };
    for (int i = 0; i < IMU_COUNT; i++) {
        float r_mm = imu_geom[i].radius_m * 1000.0f;
        ASSERT_NEAR(r_mm * cosf(imu_geom[i].angle_rad), xy_mm[i][0], 0.01f);
        ASSERT_NEAR(r_mm * sinf(imu_geom[i].angle_rad), xy_mm[i][1], 0.01f);
    }
}

/* ---- scale factors ---- */

static void test_scale_factors_match_datasheets(void) {
    imu_sample_t s[IMU_COUNT];
    mat_t z;

    /* LSM6 gyro: 1000 counts = 140 dps. */
    memset(s, 0, sizeof(s));
    s[IMU_A].gyro_z = 1000;
    imu_samples_to_meas(s, &z);
    ASSERT_NEAR(mat_get(&z, MEAS_A_GYRO, 0), 140.0f * DEG, 1e-4f);

    /* LSM6 high-g: 1000 counts = 10.417 g. Not 320/32768 = 9.766 g. */
    memset(s, 0, sizeof(s));
    s[IMU_A].accel_y = 1000;
    imu_samples_to_meas(s, &z);
    ASSERT_NEAR(fabsf(mat_get(&z, MEAS_A_TANGENTIAL, 0)), 10.417f * G_TO_MS2, 1e-3f);

    /* H3LIS: one 12-bit digit (16 counts) = 195 mg; the largest positive
     * reading, 2047 digits, is just under 400 g. */
    memset(s, 0, sizeof(s));
    s[IMU_B].accel_x = 16;
    s[IMU_C].accel_y = 0x7FF0;
    imu_samples_to_meas(s, &z);
    ASSERT_NEAR(fabsf(mat_get(&z, MEAS_B_RADIAL, 0)), 0.195f * G_TO_MS2, 1e-4f);
    ASSERT_NEAR(fabsf(mat_get(&z, MEAS_C_RADIAL, 0)), 2047.0f * 0.195f * G_TO_MS2, 0.05f);
}

/* A channel stuck at its digital rail has to convert to a value the EKF
 * recognises as saturated, or it trusts a clipped reading. */
static void test_railed_counts_are_flagged_saturated(void) {
    imu_sample_t s[IMU_COUNT];
    mat_t z;
    bool sat[MEAS_DIM];

    for (int sign = -1; sign <= 1; sign += 2) {
        int16_t rail16 = sign > 0 ? 32767 : -32768;
        int16_t rail12 = sign > 0 ? 0x7FF0 : -32768;
        memset(s, 0, sizeof(s));
        s[IMU_A].accel_x = s[IMU_A].accel_y = rail16;
        s[IMU_A].gyro_z = rail16;
        s[IMU_B].accel_x = s[IMU_B].accel_y = rail12;
        s[IMU_C].accel_x = s[IMU_C].accel_y = rail12;
        imu_samples_to_meas(s, &z);
        meas_saturation_flags(&z, sat);
        for (int row = 0; row < MEAS_DIM; row++) ASSERT_TRUE(sat[row]);
    }

    /* And a reading well inside the range is not. */
    spin_samples(200.0f, 0.0f, s);
    imu_samples_to_meas(s, &z);
    meas_saturation_flags(&z, sat);
    ASSERT_TRUE(!sat[MEAS_A_RADIAL] && !sat[MEAS_B_RADIAL] && !sat[MEAS_C_RADIAL]);
}

/* ---- axis map ---- */

/* The same 100 g of centripetal acceleration on each chip, written on
 * the axis that lies along the radius with the sign that chip gives it:
 * an axis pointing outward reads negative, one pointing at the centre
 * positive. All three radial rows must come out positive and equal. */
static void test_equal_radial_accel_reads_equal_and_positive(void) {
    const float g = 100.0f;
    imu_sample_t s[IMU_COUNT];
    memset(s, 0, sizeof(s));
    s[IMU_A].accel_x = (int16_t)-to_counts(g / g_per_count(IMU_A));  /* U4: +X outward */
    s[IMU_B].accel_x = to_counts(g / g_per_count(IMU_B));            /* U5: +X inward */
    s[IMU_C].accel_y = to_counts(g / g_per_count(IMU_C));            /* U6: +Y inward */

    mat_t z;
    imu_samples_to_meas(s, &z);

    float a = mat_get(&z, MEAS_A_RADIAL, 0);
    float b = mat_get(&z, MEAS_B_RADIAL, 0);
    float c = mat_get(&z, MEAS_C_RADIAL, 0);
    /* Within one count of each other and of the true value. */
    ASSERT_NEAR(a, g * G_TO_MS2, 0.12f);
    ASSERT_NEAR(b, g * G_TO_MS2, 0.12f);
    ASSERT_NEAR(c, g * G_TO_MS2, 0.12f);
    ASSERT_NEAR(a, b, 0.12f);
    ASSERT_NEAR(b, c, 0.12f);

    /* Purely radial input: nothing on the tangential or gyro rows. */
    ASSERT_NEAR(mat_get(&z, MEAS_A_TANGENTIAL, 0), 0.0f, 1e-6f);
    ASSERT_NEAR(mat_get(&z, MEAS_B_TANGENTIAL, 0), 0.0f, 1e-6f);
    ASSERT_NEAR(mat_get(&z, MEAS_C_TANGENTIAL, 0), 0.0f, 1e-6f);
    ASSERT_NEAR(mat_get(&z, MEAS_A_GYRO, 0), 0.0f, 1e-6f);
}

static void check_spin(float omega, float alpha, bool check_gyro) {
    imu_sample_t s[IMU_COUNT];
    mat_t z, want;
    spin_samples(omega, alpha, s);
    imu_samples_to_meas(s, &z);
    predict(omega, alpha, &want);

    /* One count of quantisation on each axis. */
    const float tol = 0.13f;
    ASSERT_NEAR(mat_get(&z, MEAS_A_RADIAL, 0),     mat_get(&want, MEAS_A_RADIAL, 0), tol);
    ASSERT_NEAR(mat_get(&z, MEAS_A_TANGENTIAL, 0), mat_get(&want, MEAS_A_TANGENTIAL, 0), tol);
    ASSERT_NEAR(mat_get(&z, MEAS_B_RADIAL, 0),     mat_get(&want, MEAS_B_RADIAL, 0), tol);
    ASSERT_NEAR(mat_get(&z, MEAS_B_TANGENTIAL, 0), mat_get(&want, MEAS_B_TANGENTIAL, 0), tol);
    ASSERT_NEAR(mat_get(&z, MEAS_C_RADIAL, 0),     mat_get(&want, MEAS_C_RADIAL, 0), tol);
    ASSERT_NEAR(mat_get(&z, MEAS_C_TANGENTIAL, 0), mat_get(&want, MEAS_C_TANGENTIAL, 0), tol);
    if (check_gyro) {
        ASSERT_NEAR(mat_get(&z, MEAS_A_GYRO, 0), mat_get(&want, MEAS_A_GYRO, 0), 0.003f);
    }
}

/* Whole chain against the EKF's own model: board geometry -> what each
 * chip reads -> imu_samples_to_meas() must equal meas_predict(). Covers
 * both spin directions and both signs of angular acceleration, below the
 * gyro's range (so its row is checked too) and at combat speed. */
static void test_spinning_body_matches_measurement_model(void) {
    check_spin(50.0f, 0.0f, true);
    check_spin(50.0f, 800.0f, true);
    check_spin(50.0f, -800.0f, true);
    check_spin(-50.0f, 800.0f, true);
    check_spin(-50.0f, -800.0f, true);
    check_spin(0.0f, 1500.0f, true);

    check_spin(300.0f, 0.0f, false);
    check_spin(300.0f, 2000.0f, false);
    check_spin(-300.0f, -2000.0f, false);
    check_spin(400.0f, -3000.0f, false);
}

int main(void) {
    RUN_TEST(test_geometry_matches_board);
    RUN_TEST(test_scale_factors_match_datasheets);
    RUN_TEST(test_railed_counts_are_flagged_saturated);
    RUN_TEST(test_equal_radial_accel_reads_equal_and_positive);
    RUN_TEST(test_spinning_body_matches_measurement_model);
    return test_report();
}
