#pragma once

/*
 * Simulated IMU bus for host tests of src/imu/latch.c and imu_spi.c.
 *
 * Models the parts of the rev 2 board the driver talks to:
 *   - an SN74HC595 whose serial input is MOSI and shift clock is SCK, so
 *     EVERY byte on the bus runs through its shift register; RCLK and
 *     /OE are GPIOs; QA/QB/QC are the three chip selects, pulled high
 *     when the outputs are blanked;
 *   - three register-file SPI slaves (one LSM6DSV320X, two H3LIS331DL)
 *     that decode R/W and address only from the first byte after their
 *     CS falls, exactly the property the driver has to respect.
 *
 * Time is simulated: SPI bytes and the delay calls advance a nanosecond
 * counter, which lets tests bound bus time and catch the latch being
 * clocked before a released CS line has risen.
 */

#include <stdbool.h>
#include <stdint.h>

enum { FAKE_IMU_A = 0, FAKE_IMU_B = 1, FAKE_IMU_C = 2, FAKE_IMU_COUNT = 3 };

#define FAKE_REG_COUNT 128

typedef struct {
    uint8_t chip;
    uint8_t reg;
    uint8_t val;
} fake_write_t;

/* Power-on state: latch contents unknown (all zero, the worst case),
 * outputs blanked by the /OE pull-up, sensors holding register defaults,
 * clock at zero, counters cleared. */
void fake_pico_reset(void);

/* Register file of one sensor, FAKE_REG_COUNT bytes, for planting output
 * data and inspecting or disturbing configuration. */
uint8_t *fake_imu_regs(int chip);

/* A chip that is absent never drives MISO (reads come back 0xFF) and
 * ignores writes. */
void fake_imu_set_present(int chip, bool present);

/* The chip ignores the bus until the simulated clock reaches this time,
 * like a sensor still booting after power-up. */
void fake_imu_set_boot_ns(int chip, uint64_t ready_at_ns);

/* Levels on the latch output pins QA..QH as a byte (bit 0 = QA). Blanked
 * outputs read as 1: the CS lines are pulled up and the rest are unused. */
uint8_t fake_latch_pins(void);
bool fake_latch_enabled(void);
/* Storage register contents regardless of /OE. */
uint8_t fake_latch_storage(void);

uint64_t fake_time_ns(void);

/* Per-chip traffic counters since reset (or fake_clear_counters). */
unsigned fake_imu_cs_cycles(int chip);   /* CS falls */
unsigned fake_imu_bytes(int chip);       /* bytes clocked while selected */
void fake_clear_counters(void);

/* Register writes accepted by the sensors since the last clear, in
 * order. Returns the count; entries are valid until the next reset. */
unsigned fake_write_log(const fake_write_t **log);

/* Protocol violations seen so far; all must stay 0. */
unsigned fake_contention_count(void);     /* two CS lines low at once */
unsigned fake_cs_glitch_count(void);      /* bus clocked while a released
                                           * CS was still rising */
unsigned fake_fs_g_live_change_count(void); /* LSM6 gyro full scale changed
                                             * while the gyro was running */

/* What the driver asked of the SPI block. */
unsigned fake_spi_baudrate(void);
bool fake_spi_is_mode0_msb_first(void);
