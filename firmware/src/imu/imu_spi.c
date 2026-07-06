#include "imu_spi.h"
#include "latch.h"
#include "hw_pins.h"

#include "hardware/spi.h"
#include "pico/stdlib.h"

/* ---- LSM6DSV320X registers (IMU-A) ---- */
#define LSM6_WHO_AM_I       0x0F
#define LSM6_WHO_AM_I_VAL   0x71
#define LSM6_IF_CFG         0x03
#define LSM6_CTRL1_XL       0x10
#define LSM6_CTRL2_G        0x11
#define LSM6_CTRL3_C        0x12
#define LSM6_OUTX_L_A       0x28
#define LSM6_OUTX_L_G       0x22

/* ---- H3LIS331DL registers (IMU-B, IMU-C) ---- */
#define H3LIS_WHO_AM_I      0x0F
#define H3LIS_WHO_AM_I_VAL  0x32
#define H3LIS_CTRL_REG1     0x20
#define H3LIS_CTRL_REG4     0x23
#define H3LIS_OUT_X_L       0x28

/* Latch bit for each IMU's CS */
static const uint8_t imu_cs_bits[IMU_COUNT] = {
    LATCH_BIT_CS_A,
    LATCH_BIT_CS_B,
    LATCH_BIT_CS_C,
};

/* SPI register read: send address with MSB=1 (read), then clock in data.
 * Caller must have already selected the target via latch. */
static void spi_read_regs(uint8_t reg, uint8_t *buf, size_t len) {
    uint8_t cmd = reg | 0x80;  /* read bit */
    if (len > 1) cmd |= 0x40;  /* auto-increment for multi-byte */
    spi_write_blocking(SPI_INST, &cmd, 1);
    spi_read_blocking(SPI_INST, 0xFF, buf, len);
}

static void spi_write_reg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg & 0x7F, val };
    spi_write_blocking(SPI_INST, buf, 2);
}

static bool lsm6_init(void) {
    latch_select(LATCH_BIT_CS_A);

    uint8_t who;
    spi_read_regs(LSM6_WHO_AM_I, &who, 1);
    if (who != LSM6_WHO_AM_I_VAL) {
        latch_deselect_all();
        return false;
    }

    /* Disable I2C/I3C interface (required before SPI works reliably) */
    spi_write_reg(LSM6_IF_CFG, 0x10);  /* I2C_I3C_DISABLE = 1 */

    /* Accel: ±320G, 1kHz ODR, high-performance mode */
    spi_write_reg(LSM6_CTRL1_XL, 0xA8);  /* ODR=1000Hz, FS=±320G */

    /* Gyro: ±4000 dps, 1kHz ODR */
    spi_write_reg(LSM6_CTRL2_G, 0xAC);   /* ODR=1000Hz, FS=±4000dps */

    /* BDU enable, IF_INC enable */
    spi_write_reg(LSM6_CTRL3_C, 0x44);

    latch_deselect_all();
    return true;
}

static bool h3lis_init(uint8_t cs_bit) {
    latch_select(cs_bit);

    uint8_t who;
    spi_read_regs(H3LIS_WHO_AM_I, &who, 1);
    if (who != H3LIS_WHO_AM_I_VAL) {
        latch_deselect_all();
        return false;
    }

    /* Normal mode, 1kHz ODR, all axes enabled */
    spi_write_reg(H3LIS_CTRL_REG1, 0x37);  /* DR=10 (1kHz), Zen=Yen=Xen=1 */

    /* ±400G full scale, BDU enable, SPI mode */
    spi_write_reg(H3LIS_CTRL_REG4, 0x90);  /* FS=±400G, BDU=1, SIM=0 (4-wire) */

    latch_deselect_all();
    return true;
}

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

    /* Init each sensor */
    if (!lsm6_init()) return false;
    if (!h3lis_init(LATCH_BIT_CS_B)) return false;
    if (!h3lis_init(LATCH_BIT_CS_C)) return false;

    return true;
}

static void read_lsm6_into(imu_sample_t *s) {
    uint8_t buf[12];
    /* Read gyro (6 bytes starting at 0x22) then accel (6 bytes starting at 0x28) */
    spi_read_regs(LSM6_OUTX_L_G, buf, 6);
    s->gyro_x = (int16_t)((buf[1] << 8) | buf[0]);
    s->gyro_y = (int16_t)((buf[3] << 8) | buf[2]);
    s->gyro_z = (int16_t)((buf[5] << 8) | buf[4]);

    spi_read_regs(LSM6_OUTX_L_A, buf, 6);
    s->accel_x = (int16_t)((buf[1] << 8) | buf[0]);
    s->accel_y = (int16_t)((buf[3] << 8) | buf[2]);
    s->accel_z = (int16_t)((buf[5] << 8) | buf[4]);
}

static void read_h3lis_into(imu_sample_t *s) {
    uint8_t buf[6];
    spi_read_regs(H3LIS_OUT_X_L | 0x40, buf, 6);  /* auto-increment */
    s->accel_x = (int16_t)((buf[1] << 8) | buf[0]);
    s->accel_y = (int16_t)((buf[3] << 8) | buf[2]);
    s->accel_z = (int16_t)((buf[5] << 8) | buf[4]);
    s->gyro_x = 0;
    s->gyro_y = 0;
    s->gyro_z = 0;
}

/* Select one IMU via the latch and read it into the sample.
 * Does NOT deselect afterward; caller deselects once when done.
 * latch_select already does disable -> load -> enable, so chaining
 * these back-to-back never leaves multiple CS lines active. */
static void select_and_read(uint8_t imu_id, imu_sample_t *s) {
    latch_select(imu_cs_bits[imu_id]);
    if (imu_id == IMU_A) {
        read_lsm6_into(s);
    } else {
        read_h3lis_into(s);
    }
}

bool imu_read_single(uint8_t imu_id, imu_sample_t *sample) {
    if (imu_id >= IMU_COUNT) return false;
    select_and_read(imu_id, sample);
    latch_deselect_all();
    return true;
}

bool imu_read_all(imu_sample_t samples[IMU_COUNT]) {
    for (int i = 0; i < IMU_COUNT; i++) {
        select_and_read(i, &samples[i]);
    }
    latch_deselect_all();
    return true;
}
