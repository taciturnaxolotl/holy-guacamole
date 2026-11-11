#pragma once

/*
 * Host stand-in for the pico-sdk hardware/spi.h, covering only what the
 * IMU driver calls. Bytes written here are clocked into the simulated
 * board in fake_pico.c. See fake_pico.h.
 */

#include <stddef.h>
#include <stdint.h>

typedef struct spi_inst spi_inst_t;
extern spi_inst_t *const fake_spi0;
#define spi0 fake_spi0

typedef enum { SPI_CPHA_0 = 0, SPI_CPHA_1 = 1 } spi_cpha_t;
typedef enum { SPI_CPOL_0 = 0, SPI_CPOL_1 = 1 } spi_cpol_t;
typedef enum { SPI_LSB_FIRST = 0, SPI_MSB_FIRST = 1 } spi_order_t;

unsigned int spi_init(spi_inst_t *spi, unsigned int baudrate);
void spi_set_format(spi_inst_t *spi, unsigned int data_bits, spi_cpol_t cpol,
                    spi_cpha_t cpha, spi_order_t order);
int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len);
int spi_read_blocking(spi_inst_t *spi, uint8_t repeated_tx_data, uint8_t *dst,
                      size_t len);
