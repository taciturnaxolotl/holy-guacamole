#pragma once

/*
 * Holy Guacamole carrier PCB (rev 2) pin assignments.
 * Matches the pin table in docs/spec.md. GPIO numbers are for the
 * Seeed XIAO RP2350 (RP2350A); see the SDK's boards/seeed_xiao_rp2350.h.
 */

/* SPI bus (shared: IMUs + SN74HC595 latch) */
#define PIN_SPI_SCK   2   /* XIAO D8/GPIO2 */
#define PIN_SPI_MOSI  3   /* XIAO D10/GPIO3 */
#define PIN_SPI_MISO  4   /* XIAO D9/GPIO4 */
#define SPI_INST      spi0

/* SN74HC595 latch control */
#define PIN_SEL_OE_N  28  /* XIAO D2/A2/GPIO28, active-low output enable */
#define PIN_SEL_LAT   5   /* XIAO D3/GPIO5, latch clock */

/* Latch bit assignments (active-low outputs); QD-QH are NC */
#define LATCH_BIT_CS_A     0  /* QA / pin 15 -> CS_A */
#define LATCH_BIT_CS_B     1  /* QB / pin 1  -> CS_B */
#define LATCH_BIT_CS_C     2  /* QC / pin 2  -> CS_C */

/* Safe latch image: all outputs inactive (high) */
#define LATCH_SAFE  0xFF

/* DSHOT bidirectional (direct RP2350 GPIO, not through latch) */
#define PIN_DSHOT1    6   /* XIAO D4/SDA/GPIO6 -> AM32 ch1 */
#define PIN_DSHOT2    7   /* XIAO D5/SCL/GPIO7 -> AM32 ch2 */

/* CRSF UART to ELRS receiver */
#define PIN_CRSF_TX   0   /* XIAO D6/TX/GPIO0 */
#define PIN_CRSF_RX   1   /* XIAO D7/RX/GPIO1 */
#define CRSF_UART     uart0
#define CRSF_BAUD     420000

/* Battery voltage sense */
#define PIN_VBAT_ADC  26  /* XIAO D0/A0/GPIO26 */
#define ADC_VBAT_CHAN 0   /* ADC channel for GPIO26 */

/* TinySLED heading/status LEDs: AO3402 Q1 gate, high = lit */
#define PIN_HEAD_LED  27  /* XIAO D1/A1/GPIO27 */
