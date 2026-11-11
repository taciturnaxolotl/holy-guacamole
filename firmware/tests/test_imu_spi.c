#include "test_assert.h"

#include "fake_pico/fake_pico.h"
#include "imu/imu_spi.h"
#include "imu/latch.h"

#include <string.h>

/*
 * Driver tests against the simulated bus in fake_pico/: the SN74HC595
 * chip-select latch plus three register-file SPI slaves that only decode
 * an address on the first byte after their CS falls. Register values are
 * written out as literals from the datasheets (ST DS14623 Rev 3 for the
 * LSM6DSV320X, DS9012 Rev 5 for the H3LIS331DL), not taken from the
 * driver, so a wrong constant there fails here.
 */

/* LSM6DSV320X */
#define A_IF_CFG       0x03
#define A_WHO_AM_I     0x0F
#define A_CTRL1        0x10
#define A_CTRL2        0x11
#define A_CTRL3        0x12
#define A_CTRL6        0x15
#define A_OUT_G        0x22
#define A_OUT_XL_LOWG  0x28
#define A_OUT_XL_HG    0x34
#define A_CTRL1_XL_HG  0x4E
/* H3LIS331DL */
#define H_WHO_AM_I     0x0F
#define H_CTRL_REG1    0x20
#define H_CTRL_REG4    0x23
#define H_OUT          0x28

static void assert_bus_clean(void) {
    ASSERT_TRUE(fake_contention_count() == 0);
    ASSERT_TRUE(fake_cs_glitch_count() == 0);
    ASSERT_TRUE(fake_fs_g_live_change_count() == 0);
    /* Idle state: outputs blanked and the safe image latched behind them. */
    ASSERT_TRUE(!fake_latch_enabled());
    ASSERT_TRUE(fake_latch_pins() == 0xFF);
    ASSERT_TRUE(fake_latch_storage() == 0xFF);
}

static void put_le16(uint8_t *p, int16_t v) {
    p[0] = (uint8_t)((uint16_t)v & 0xFF);
    p[1] = (uint8_t)((uint16_t)v >> 8);
}

/* ---- latch ---- */

static void test_latch_init_does_not_pulse_cs(void) {
    fake_pico_reset();
    latch_init();
    ASSERT_TRUE(!fake_latch_enabled());
    for (int i = 0; i < FAKE_IMU_COUNT; i++) ASSERT_TRUE(fake_imu_cs_cycles(i) == 0);
}

/* QA is CS_A: selecting it must pull QA low and nothing else. With the
 * image bit-reversed on the way out this came out as QH (0x7F). */
static void test_latch_select_drives_only_the_named_output(void) {
    fake_pico_reset();
    latch_init();

    latch_select(LATCH_BIT_CS_A);
    ASSERT_TRUE(fake_latch_enabled());
    ASSERT_TRUE(fake_latch_pins() == 0xFE);

    latch_select(LATCH_BIT_CS_B);
    ASSERT_TRUE(fake_latch_pins() == 0xFD);

    latch_select(LATCH_BIT_CS_C);
    ASSERT_TRUE(fake_latch_pins() == 0xFB);

    latch_deselect_all();
    ASSERT_TRUE(!fake_latch_enabled());
    ASSERT_TRUE(fake_latch_pins() == 0xFF);
    ASSERT_TRUE(fake_latch_storage() == 0xFF);

    ASSERT_TRUE(fake_contention_count() == 0);
    ASSERT_TRUE(fake_cs_glitch_count() == 0);
}

/* Re-selecting the same target has to produce a new CS falling edge, or
 * back-to-back register accesses on one chip run together. */
static void test_latch_reselect_is_a_new_cs_cycle(void) {
    fake_pico_reset();
    latch_init();
    latch_select(LATCH_BIT_CS_A);
    latch_select(LATCH_BIT_CS_A);
    latch_deselect_all();
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_A) == 2);
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_B) == 0);
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_C) == 0);
}

/* ---- init ---- */

static void test_init_writes_intended_config(void) {
    fake_pico_reset();

    uint8_t before[FAKE_IMU_COUNT][FAKE_REG_COUNT];
    for (int i = 0; i < FAKE_IMU_COUNT; i++) memcpy(before[i], fake_imu_regs(i), FAKE_REG_COUNT);

    ASSERT_TRUE(imu_init());

    ASSERT_TRUE(fake_spi_is_mode0_msb_first());
    ASSERT_TRUE(fake_spi_baudrate() > 0 && fake_spi_baudrate() <= 10000000u);

    const uint8_t *a = fake_imu_regs(FAKE_IMU_A);
    ASSERT_TRUE(a[A_IF_CFG] == 0x01);       /* I2C_I3C_disable */
    ASSERT_TRUE(a[A_CTRL1] == 0x00);        /* low-g accel off */
    ASSERT_TRUE(a[A_CTRL2] == 0x09);        /* gyro 960 Hz, high-performance */
    ASSERT_TRUE(a[A_CTRL3] == 0x44);        /* BDU | IF_INC */
    ASSERT_TRUE(a[A_CTRL6] == 0x0D);        /* +/-4000 dps, bit 3 kept at 1 */
    ASSERT_TRUE(a[A_CTRL1_XL_HG] == 0xA4);  /* regout | 960 Hz | +/-320 g */

    for (int i = FAKE_IMU_B; i <= FAKE_IMU_C; i++) {
        const uint8_t *h = fake_imu_regs(i);
        ASSERT_TRUE(h[H_CTRL_REG1] == 0x3F);  /* normal, 1 kHz, XYZ */
        ASSERT_TRUE(h[H_CTRL_REG4] == 0xB0);  /* BDU, +/-400 g */
    }

    /* Nothing else was touched: a mis-framed access lands in some other
     * register. */
    static const uint8_t a_cfg[] = { A_IF_CFG, A_CTRL1, A_CTRL2, A_CTRL3, A_CTRL6, A_CTRL1_XL_HG };
    static const uint8_t h_cfg[] = { H_CTRL_REG1, H_CTRL_REG4 };
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        const uint8_t *cfg = i == FAKE_IMU_A ? a_cfg : h_cfg;
        size_t n = i == FAKE_IMU_A ? sizeof(a_cfg) : sizeof(h_cfg);
        for (size_t k = 0; k < n; k++) before[i][cfg[k]] = fake_imu_regs(i)[cfg[k]];
        ASSERT_TRUE(memcmp(before[i], fake_imu_regs(i), FAKE_REG_COUNT) == 0);
    }

    assert_bus_clean();
}

/* Every register access is its own CS cycle of exactly two bytes. */
static void test_init_frames_each_register_access(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        ASSERT_TRUE(fake_imu_cs_cycles(i) > 0);
        ASSERT_TRUE(fake_imu_bytes(i) == 2 * fake_imu_cs_cycles(i));
    }
}

static void test_init_rejects_wrong_part(void) {
    fake_pico_reset();
    fake_imu_regs(FAKE_IMU_A)[A_WHO_AM_I] = 0x71;  /* some other LSM6 */
    ASSERT_TRUE(!imu_init());
    assert_bus_clean();

    fake_pico_reset();
    fake_imu_regs(FAKE_IMU_C)[H_WHO_AM_I] = 0x33;
    ASSERT_TRUE(!imu_init());
}

static void test_init_fails_when_a_sensor_is_missing(void) {
    for (int missing = 0; missing < FAKE_IMU_COUNT; missing++) {
        fake_pico_reset();
        fake_imu_set_present(missing, false);
        ASSERT_TRUE(!imu_init());
        assert_bus_clean();
    }
}

/* A sensor that is still loading its trim when the MCU gets going must
 * not be written off. */
static void test_init_waits_for_a_booting_sensor(void) {
    fake_pico_reset();
    fake_imu_set_boot_ns(FAKE_IMU_A, 12u * 1000000u);
    fake_imu_set_boot_ns(FAKE_IMU_B, 6u * 1000000u);
    ASSERT_TRUE(imu_init());
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_A)[A_CTRL1_XL_HG] == 0xA4);
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_B)[H_CTRL_REG4] == 0xB0);
    ASSERT_TRUE(imu_health_check());
}

/* imu_init() may simply be called again (main can use it as a heavier
 * recovery path): the second pass must not pulse a CS line while the
 * latch GPIOs are set up again, and must leave the same configuration. */
static void test_init_can_be_called_again(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());
    ASSERT_TRUE(imu_init());
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_A)[A_CTRL2] == 0x09);
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_A)[A_CTRL6] == 0x0D);
    ASSERT_TRUE(imu_health_check());
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        ASSERT_TRUE(fake_imu_bytes(i) == 2 * fake_imu_cs_cycles(i));
    }
    assert_bus_clean();
}

/* ---- sample read ---- */

static void test_read_all_returns_planted_samples(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());

    uint8_t *a = fake_imu_regs(FAKE_IMU_A);
    put_le16(&a[A_OUT_G + 0], 0x1234);
    put_le16(&a[A_OUT_G + 2], -2);
    put_le16(&a[A_OUT_G + 4], -32768);
    put_le16(&a[A_OUT_XL_HG + 0], 0x0102);
    put_le16(&a[A_OUT_XL_HG + 2], -300);
    put_le16(&a[A_OUT_XL_HG + 4], 32767);
    /* Decoys where the old driver looked: the low-g outputs at 28h, and
     * 62h/68h, which is where OR-ing 0x40 into the address ends up. */
    memset(&a[A_OUT_XL_LOWG], 0x5A, 6);
    memset(&a[0x62], 0xA5, 12);

    uint8_t *b = fake_imu_regs(FAKE_IMU_B);
    put_le16(&b[H_OUT + 0], 0x7FF0);
    put_le16(&b[H_OUT + 2], -16);
    put_le16(&b[H_OUT + 4], 0x0010);
    uint8_t *c = fake_imu_regs(FAKE_IMU_C);
    put_le16(&c[H_OUT + 0], -4096);
    put_le16(&c[H_OUT + 2], 0x0550);
    put_le16(&c[H_OUT + 4], -32768);

    fake_clear_counters();
    imu_sample_t s[IMU_COUNT];
    memset(s, 0x77, sizeof(s));
    ASSERT_TRUE(imu_read_all(s));

    ASSERT_TRUE(s[IMU_A].gyro_x == 0x1234);
    ASSERT_TRUE(s[IMU_A].gyro_y == -2);
    ASSERT_TRUE(s[IMU_A].gyro_z == -32768);
    ASSERT_TRUE(s[IMU_A].accel_x == 0x0102);
    ASSERT_TRUE(s[IMU_A].accel_y == -300);
    ASSERT_TRUE(s[IMU_A].accel_z == 32767);

    ASSERT_TRUE(s[IMU_B].accel_x == 0x7FF0);
    ASSERT_TRUE(s[IMU_B].accel_y == -16);
    ASSERT_TRUE(s[IMU_B].accel_z == 0x0010);
    ASSERT_TRUE(s[IMU_B].gyro_x == 0 && s[IMU_B].gyro_y == 0 && s[IMU_B].gyro_z == 0);

    ASSERT_TRUE(s[IMU_C].accel_x == -4096);
    ASSERT_TRUE(s[IMU_C].accel_y == 0x0550);
    ASSERT_TRUE(s[IMU_C].accel_z == -32768);
    ASSERT_TRUE(s[IMU_C].gyro_x == 0 && s[IMU_C].gyro_y == 0 && s[IMU_C].gyro_z == 0);

    /* Two bursts on the LSM6 (gyro, high-g), one on each H3LIS, each a
     * command byte plus six data bytes; no register is written. */
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_A) == 2);
    ASSERT_TRUE(fake_imu_bytes(FAKE_IMU_A) == 14);
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_B) == 1);
    ASSERT_TRUE(fake_imu_bytes(FAKE_IMU_B) == 7);
    ASSERT_TRUE(fake_imu_cs_cycles(FAKE_IMU_C) == 1);
    ASSERT_TRUE(fake_imu_bytes(FAKE_IMU_C) == 7);
    ASSERT_TRUE(fake_write_log(NULL) == 0);

    assert_bus_clean();
}

/* Reading must not depend on what the latch shift register was left
 * holding by the previous cycle's data bytes. */
static void test_read_all_is_repeatable(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());
    put_le16(&fake_imu_regs(FAKE_IMU_C)[H_OUT], 1234);

    for (int i = 0; i < 5; i++) {
        imu_sample_t s[IMU_COUNT];
        put_le16(&fake_imu_regs(FAKE_IMU_A)[A_OUT_XL_HG], (int16_t)(100 * i));
        ASSERT_TRUE(imu_read_all(s));
        ASSERT_TRUE(s[IMU_A].accel_x == 100 * i);
        ASSERT_TRUE(s[IMU_C].accel_x == 1234);
    }
    assert_bus_clean();
}

/* ---- health ---- */

static void test_health_check_passes_and_is_read_only(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());
    fake_clear_counters();
    ASSERT_TRUE(imu_health_check());
    ASSERT_TRUE(imu_health_check());
    ASSERT_TRUE(fake_write_log(NULL) == 0);
    assert_bus_clean();
}

static void test_health_check_catches_each_disturbed_register(void) {
    static const struct { int chip; uint8_t reg; uint8_t bad; } cases[] = {
        { FAKE_IMU_A, A_WHO_AM_I,    0xFF },
        { FAKE_IMU_A, A_IF_CFG,      0x00 },
        { FAKE_IMU_A, A_CTRL1,       0x09 },
        { FAKE_IMU_A, A_CTRL2,       0x00 },  /* gyro back in power-down */
        { FAKE_IMU_A, A_CTRL3,       0x04 },  /* BDU lost */
        { FAKE_IMU_A, A_CTRL6,       0x0C },  /* +/-2000 dps */
        { FAKE_IMU_A, A_CTRL1_XL_HG, 0x00 },  /* high-g channel off */
        { FAKE_IMU_B, H_WHO_AM_I,    0x00 },
        { FAKE_IMU_B, H_CTRL_REG1,   0x07 },  /* power-on default */
        { FAKE_IMU_B, H_CTRL_REG4,   0x90 },  /* +/-200 g */
        { FAKE_IMU_C, H_CTRL_REG1,   0x37 },  /* 400 Hz */
        { FAKE_IMU_C, H_CTRL_REG4,   0x00 },
    };

    fake_pico_reset();
    ASSERT_TRUE(imu_init());

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        uint8_t *reg = &fake_imu_regs(cases[i].chip)[cases[i].reg];
        uint8_t good = *reg;
        *reg = cases[i].bad;
        ASSERT_TRUE(!imu_health_check());
        *reg = good;
        ASSERT_TRUE(imu_health_check());
    }
    assert_bus_clean();
}

static void test_health_check_catches_a_sensor_dropping_out(void) {
    for (int chip = 0; chip < FAKE_IMU_COUNT; chip++) {
        fake_pico_reset();
        ASSERT_TRUE(imu_init());
        fake_imu_set_present(chip, false);
        ASSERT_TRUE(!imu_health_check());
        ASSERT_TRUE(!imu_reinit());
        fake_imu_set_present(chip, true);
        ASSERT_TRUE(imu_reinit());
    }
}

/* A sensor that browned out comes back with power-on defaults; reinit
 * has to bring it back without the bus setup being redone. */
static void test_reinit_restores_a_reset_sensor(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());

    uint8_t *a = fake_imu_regs(FAKE_IMU_A);
    a[A_IF_CFG] = 0x00;
    a[A_CTRL2] = 0x00;
    a[A_CTRL6] = 0x08;
    a[A_CTRL1_XL_HG] = 0x00;
    uint8_t *c = fake_imu_regs(FAKE_IMU_C);
    c[H_CTRL_REG1] = 0x07;
    c[H_CTRL_REG4] = 0x00;

    ASSERT_TRUE(!imu_health_check());
    ASSERT_TRUE(imu_reinit());
    ASSERT_TRUE(a[A_IF_CFG] == 0x01 && a[A_CTRL2] == 0x09 && a[A_CTRL6] == 0x0D &&
                a[A_CTRL1_XL_HG] == 0xA4);
    ASSERT_TRUE(c[H_CTRL_REG1] == 0x3F && c[H_CTRL_REG4] == 0xB0);
    ASSERT_TRUE(imu_health_check());
    assert_bus_clean();
}

/* DS14623 9.19: the gyro full scale may only change in power-down. On a
 * warm reinit the gyro is running, so it has to be stopped first. */
static void test_reinit_changes_gyro_range_only_in_power_down(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());

    fake_imu_regs(FAKE_IMU_A)[A_CTRL6] = 0x0C;  /* range corrupted, gyro still running */
    ASSERT_TRUE(!imu_health_check());
    ASSERT_TRUE(imu_reinit());
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_A)[A_CTRL6] == 0x0D);
    ASSERT_TRUE(fake_imu_regs(FAKE_IMU_A)[A_CTRL2] == 0x09);
    ASSERT_TRUE(fake_fs_g_live_change_count() == 0);
}

/* Bus time only (SPI bytes at the configured clock plus the driver's own
 * delays); CPU overhead is not modelled. Bounds are loose on purpose:
 * they exist to catch a sleep or a pile of extra transactions creeping
 * into calls the sensor loop makes. */
static void test_bus_time_budget(void) {
    fake_pico_reset();
    ASSERT_TRUE(imu_init());

    imu_sample_t s[IMU_COUNT];
    uint64_t t0 = fake_time_ns();
    imu_read_all(s);
    uint64_t read_ns = fake_time_ns() - t0;

    t0 = fake_time_ns();
    ASSERT_TRUE(imu_health_check());
    uint64_t health_ns = fake_time_ns() - t0;

    t0 = fake_time_ns();
    ASSERT_TRUE(imu_reinit());
    uint64_t reinit_ns = fake_time_ns() - t0;

    printf("    bus time: read_all %.1f us, health_check %.1f us, reinit %.1f us\n",
           (double)read_ns / 1e3, (double)health_ns / 1e3, (double)reinit_ns / 1e3);
    ASSERT_TRUE(read_ns < 60u * 1000u);
    ASSERT_TRUE(health_ns < 200u * 1000u);
    ASSERT_TRUE(reinit_ns < 400u * 1000u);
}

int main(void) {
    RUN_TEST(test_latch_init_does_not_pulse_cs);
    RUN_TEST(test_latch_select_drives_only_the_named_output);
    RUN_TEST(test_latch_reselect_is_a_new_cs_cycle);
    RUN_TEST(test_init_writes_intended_config);
    RUN_TEST(test_init_frames_each_register_access);
    RUN_TEST(test_init_rejects_wrong_part);
    RUN_TEST(test_init_fails_when_a_sensor_is_missing);
    RUN_TEST(test_init_waits_for_a_booting_sensor);
    RUN_TEST(test_init_can_be_called_again);
    RUN_TEST(test_read_all_returns_planted_samples);
    RUN_TEST(test_read_all_is_repeatable);
    RUN_TEST(test_health_check_passes_and_is_read_only);
    RUN_TEST(test_health_check_catches_each_disturbed_register);
    RUN_TEST(test_health_check_catches_a_sensor_dropping_out);
    RUN_TEST(test_reinit_restores_a_reset_sensor);
    RUN_TEST(test_reinit_changes_gyro_range_only_in_power_down);
    RUN_TEST(test_bus_time_budget);
    return test_report();
}
