#include "imu_spi.h"
#include "latch.h"
#include "hw_pins.h"

#include "hardware/spi.h"
#include "pico/stdlib.h"

/* Both parts: the first byte after CS falls carries the read flag in bit 7
 * and the register address below it. Nothing after that byte is decoded
 * as an address, so every register access needs its own CS cycle. */
#define SPI_READ                    0x80

/* ---- LSM6DSV320X (IMU-A). Source: ST DS14623 Rev 3, sections as noted. ---- */
#define LSM6DSV320X_IF_CFG                  0x03  /* 9.3 */
#define LSM6DSV320X_WHO_AM_I                0x0F  /* 9.13 */
#define LSM6DSV320X_WHO_AM_I_VAL            0x73  /* 9.13: fixed at 73h */
#define LSM6DSV320X_CTRL1                   0x10  /* 9.14: low-g accel ODR/mode */
#define LSM6DSV320X_CTRL2                   0x11  /* 9.15: gyro ODR/mode */
#define LSM6DSV320X_CTRL3                   0x12  /* 9.16: BDU, IF_INC */
#define LSM6DSV320X_CTRL6                   0x15  /* 9.19: gyro full scale */
#define LSM6DSV320X_OUTX_L_G                0x22  /* 9.30-9.32: gyro X/Y/Z, 22h..27h */
#define LSM6DSV320X_UI_OUTX_L_A_OIS_HG      0x34  /* 9.39-9.41: high-g X/Y/Z, 34h..39h */
#define LSM6DSV320X_CTRL1_XL_HG             0x4E  /* 9.53: high-g accel enable/ODR/FS */

/* ---- H3LIS331DL (IMU-B, IMU-C). Source: ST DS9012 Rev 5. ---- */
#define H3LIS_WHO_AM_I      0x0F  /* 8.1 */
#define H3LIS_WHO_AM_I_VAL  0x32  /* 8.1 */
#define H3LIS_CTRL_REG1     0x20  /* 8.2 */
#define H3LIS_CTRL_REG4     0x23  /* 8.5 */
#define H3LIS_OUT_X_L       0x28  /* 8.10-8.12: X/Y/Z, 28h..2Dh */
/* 6.2: bit 6 of the command byte (MS) auto-increments the address. Only
 * this part has it; on the LSM6DSV320X bit 6 is address bit 6 and
 * auto-increment is the IF_INC bit of CTRL3 instead. */
#define H3LIS_SPI_MS        0x40

typedef struct {
    uint8_t reg;
    uint8_t val;
} reg_cfg_t;

/* Written in this order by lsm6_configure(), read back by lsm6_check(). */
static const reg_cfg_t lsm6_cfg[] = {
    /* 9.3: I2C_I3C_disable is bit 0. The board is SPI only, and with the
     * block enabled clock edges meant for the other parts reach its
     * I2C/I3C decoder while CS is high. */
    { LSM6DSV320X_IF_CFG, 0x01 },
    /* 9.16: BDU (bit 6) so a 16-bit sample cannot tear, IF_INC (bit 2)
     * so a burst read walks X/Y/Z. Both are also the power-on default. */
    { LSM6DSV320X_CTRL3, 0x44 },
    /* 9.14: ODR_XL = 0000, low-g accelerometer off. Combat loads are far
     * beyond its 16 g, and 6.1.2 only lets the high-g channel run with
     * the low-g one in high-performance mode (000) or off. */
    { LSM6DSV320X_CTRL1, 0x00 },
    /* 9.19: FS_G = 101 (+/-4000 dps); bit 3 must be written as 1. */
    { LSM6DSV320X_CTRL6, 0x0D },
    /* 9.15, table 57: ODR_G = 1001 (960 Hz), OP_MODE_G = 000
     * (high-performance). */
    { LSM6DSV320X_CTRL2, 0x09 },
    /* 9.53, tables 147-150: XL_HG_REGOUT_EN (bit 7) routes the high-g
     * channel to 34h..39h, ODR_XL_HG = 100 (960 Hz), FS_XL_HG = 100
     * (+/-320 g). */
    { LSM6DSV320X_CTRL1_XL_HG, 0xA4 },
};

static const reg_cfg_t h3lis_cfg[] = {
    /* 8.2, tables 15-16: PM = 001 (normal mode), DR = 11 (1000 Hz,
     * 780 Hz low-pass), Zen | Yen | Xen. */
    { H3LIS_CTRL_REG1, 0x3F },
    /* 8.5: BDU (bit 7), FS = 11 (+/-400 g), BLE = 0 (LSB at the lower
     * address), SIM = 0 (4-wire). */
    { H3LIS_CTRL_REG4, 0xB0 },
};

#define COUNT_OF(a) (sizeof(a) / sizeof((a)[0]))

/* Latch bit for each IMU's CS */
static const uint8_t imu_cs_bits[IMU_COUNT] = {
    LATCH_BIT_CS_A,
    LATCH_BIT_CS_B,
    LATCH_BIT_CS_C,
};

/* One complete SPI read transaction: CS low, command byte, len data
 * bytes, CS high. cmd is the full first byte (see SPI_READ). CS is
 * released by blanking the latch; the safe image is reloaded once by the
 * public entry points rather than after every transaction. */
static void imu_xfer_read(uint8_t cs_bit, uint8_t cmd, uint8_t *buf, size_t len) {
    latch_select(cs_bit);
    spi_write_blocking(SPI_INST, &cmd, 1);
    spi_read_blocking(SPI_INST, 0xFF, buf, len);
    latch_disable();
}

/* One complete SPI write transaction of a single register. */
static void imu_xfer_write(uint8_t cs_bit, uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg & (uint8_t)~SPI_READ, val };
    latch_select(cs_bit);
    spi_write_blocking(SPI_INST, buf, 2);
    latch_disable();
}

static uint8_t imu_read_reg(uint8_t cs_bit, uint8_t reg) {
    uint8_t val;
    imu_xfer_read(cs_bit, SPI_READ | reg, &val, 1);
    return val;
}

static bool regs_match(uint8_t cs_bit, uint8_t who_reg, uint8_t who_val,
                       const reg_cfg_t *cfg, size_t n) {
    if (imu_read_reg(cs_bit, who_reg) != who_val) return false;
    for (size_t i = 0; i < n; i++) {
        if (imu_read_reg(cs_bit, cfg[i].reg) != cfg[i].val) return false;
    }
    return true;
}

static bool lsm6_check(void) {
    return regs_match(LATCH_BIT_CS_A, LSM6DSV320X_WHO_AM_I, LSM6DSV320X_WHO_AM_I_VAL,
                      lsm6_cfg, COUNT_OF(lsm6_cfg));
}

static bool h3lis_check(uint8_t cs_bit) {
    return regs_match(cs_bit, H3LIS_WHO_AM_I, H3LIS_WHO_AM_I_VAL,
                      h3lis_cfg, COUNT_OF(h3lis_cfg));
}

static void lsm6_configure(void) {
    /* 9.19 note 1: FS_G may only be changed with the gyroscope in
     * power-down. It already is after power-up, but not when this runs
     * again on a sensor that is still configured. */
    imu_xfer_write(LATCH_BIT_CS_A, LSM6DSV320X_CTRL2, 0x00);
    for (size_t i = 0; i < COUNT_OF(lsm6_cfg); i++) {
        imu_xfer_write(LATCH_BIT_CS_A, lsm6_cfg[i].reg, lsm6_cfg[i].val);
    }
}

static void h3lis_configure(uint8_t cs_bit) {
    for (size_t i = 0; i < COUNT_OF(h3lis_cfg); i++) {
        imu_xfer_write(cs_bit, h3lis_cfg[i].reg, h3lis_cfg[i].val);
    }
}

bool imu_health_check(void) {
    bool ok = lsm6_check() &&
              h3lis_check(LATCH_BIT_CS_B) &&
              h3lis_check(LATCH_BIT_CS_C);
    latch_deselect_all();
    return ok;
}

bool imu_reinit(void) {
    lsm6_configure();
    h3lis_configure(LATCH_BIT_CS_B);
    h3lis_configure(LATCH_BIT_CS_C);
    return imu_health_check();
}

/* The sensors share the MCU's 3V3 rail and load their trim from
 * non-volatile memory after power-up; until that is done they may not
 * answer, and neither datasheet says how long it takes. Keep trying for
 * about 50 ms before calling one missing. */
#define IMU_INIT_ATTEMPTS  25
#define IMU_INIT_RETRY_MS  2

bool imu_init(void) {
    /* Configure SPI at 10MHz, mode 0 (CPOL=0, CPHA=0).
     * Mode 0 keeps SCK idle low, preventing deselected H3LIS331DL
     * from misinterpreting bus traffic as I2C when CS is high. */
    spi_init(SPI_INST, 10000000);
    spi_set_format(SPI_INST, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);

    gpio_set_function(PIN_SPI_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SPI_MISO, GPIO_FUNC_SPI);

    /* Initialize latch first */
    latch_init();

    for (int attempt = 0; attempt < IMU_INIT_ATTEMPTS; attempt++) {
        if (imu_reinit()) return true;
        sleep_ms(IMU_INIT_RETRY_MS);
    }
    return false;
}

static int16_t le16(const uint8_t *p) {
    return (int16_t)(((uint16_t)p[1] << 8) | p[0]);
}

static void read_lsm6_into(imu_sample_t *s) {
    uint8_t buf[6];

    /* Gyro and high-g outputs are 12 registers apart (the low-g and
     * OIS/EIS outputs sit between them), so they are two transactions.
     * No 0x40 here: it would turn 22h into 62h. */
    imu_xfer_read(LATCH_BIT_CS_A, SPI_READ | LSM6DSV320X_OUTX_L_G, buf, 6);
    s->gyro_x = le16(&buf[0]);
    s->gyro_y = le16(&buf[2]);
    s->gyro_z = le16(&buf[4]);

    imu_xfer_read(LATCH_BIT_CS_A, SPI_READ | LSM6DSV320X_UI_OUTX_L_A_OIS_HG, buf, 6);
    s->accel_x = le16(&buf[0]);
    s->accel_y = le16(&buf[2]);
    s->accel_z = le16(&buf[4]);
}

static void read_h3lis_into(uint8_t cs_bit, imu_sample_t *s) {
    uint8_t buf[6];
    imu_xfer_read(cs_bit, SPI_READ | H3LIS_SPI_MS | H3LIS_OUT_X_L, buf, 6);
    s->accel_x = le16(&buf[0]);
    s->accel_y = le16(&buf[2]);
    s->accel_z = le16(&buf[4]);
    s->gyro_x = 0;
    s->gyro_y = 0;
    s->gyro_z = 0;
}

bool imu_read_all(imu_sample_t samples[IMU_COUNT]) {
    read_lsm6_into(&samples[IMU_A]);
    read_h3lis_into(imu_cs_bits[IMU_B], &samples[IMU_B]);
    read_h3lis_into(imu_cs_bits[IMU_C], &samples[IMU_C]);
    latch_deselect_all();
    return true;
}
