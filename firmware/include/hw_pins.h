#pragma once

/*
 * Holy Guacamole carrier PCB pin assignments.
 * Single source of truth matching circuit.py / spec.md pin table.
 */

/* SPI bus (shared: IMUs + SN74HC595 latch + SK9822 buffer inputs) */
#define PIN_SPI_SCK   2   /* XIAO D8/GPIO2 */
#define PIN_SPI_MOSI  3   /* XIAO D10/GPIO3 */
#define PIN_SPI_MISO  4   /* XIAO D9/GPIO4 */
#define SPI_INST      spi0

/* SN74HC595 latch control */
#define PIN_SEL_OE_N  42  /* XIAO D2/A2/GPIO42, active-low output enable */
#define PIN_SEL_LAT   43  /* XIAO D3/A3/GPIO43, latch clock */

/* Latch bit assignments (active-low outputs) */
#define LATCH_BIT_CS_A     0  /* QA / pin 15 -> CS_A */
#define LATCH_BIT_CS_B     1  /* QB / pin 1  -> CS_B */
#define LATCH_BIT_CS_C     2  /* QC / pin 2  -> CS_C */
#define LATCH_BIT_LED_OE_N 3  /* QD / pin 3  -> LED_OE_N */

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
#define PIN_VBAT_ADC  40  /* XIAO A0/D0/GPIO40 */
#define ADC_VBAT_CHAN 0   /* ADC channel for GPIO40 */

/* Heading LED MOSFET gate */
#define PIN_HEAD_LED  41  /* XIAO A1/D1/GPIO41 */

/* SWD debug (repurposed for ESP32 UART in first-rev bodge;
 * SWD not used in production. Heading LED GPIO41 is DNP.) */
#define PIN_SWDIO     23   /* ESP32 TX -> RP2350 RX */
#define PIN_SWDCK     24   /* ESP32 RX -> RP2350 TX */
