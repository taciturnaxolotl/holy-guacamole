#include "latch.h"
#include "hw_pins.h"

#include "hardware/spi.h"
#include "pico/stdlib.h"

/* Once the outputs are blanked the CS lines are held high only by their
 * 10k pull-ups, so they rise on an RC edge (a few hundred ns for a few
 * tens of pF, estimated, not measured). Wait that out before clocking
 * the latch: a sensor that still sees CS low takes the first SCK edges
 * of the latch byte as extra bits of the transaction it just finished. */
#define CS_RELEASE_SETTLE_US 1

void latch_init(void) {
    /* Level before direction: gpio_init() leaves the output latch at 0,
     * so switching to output first would enable the '595 for an instant
     * with whatever its storage register holds and pulse the CS lines. */
    gpio_init(PIN_SEL_OE_N);
    gpio_put(PIN_SEL_OE_N, 1);  /* start blanked (outputs high-Z) */
    gpio_set_dir(PIN_SEL_OE_N, GPIO_OUT);

    gpio_init(PIN_SEL_LAT);
    gpio_put(PIN_SEL_LAT, 0);   /* start low */
    gpio_set_dir(PIN_SEL_LAT, GPIO_OUT);
}

void latch_load(uint8_t image) {
    /* No bit reversal. SPI sends MSB first and the SN74HC595 clocks SER
     * into its first stage (QA) while every other stage takes the one
     * before it (TI SCLS041J, table 8-1). After 8 clocks the last bit
     * sent sits on QA and the first on QH, so bit n of the image lands
     * on the output LATCH_BIT_* names: bit 0 = QA = CS_A. */
    spi_write_blocking(SPI_INST, &image, 1);

    /* Pulse SEL_LAT to transfer shift register to output latch */
    gpio_put(PIN_SEL_LAT, 1);
    busy_wait_us_32(1);
    gpio_put(PIN_SEL_LAT, 0);
}

void latch_enable(void) {
    gpio_put(PIN_SEL_OE_N, 0);
}

void latch_disable(void) {
    gpio_put(PIN_SEL_OE_N, 1);
}

void latch_select(uint8_t bit) {
    latch_disable();
    busy_wait_us_32(CS_RELEASE_SETTLE_US);
    uint8_t image = LATCH_SAFE;
    image &= (uint8_t)~(1u << bit);
    latch_load(image);
    latch_enable();
}

void latch_deselect_all(void) {
    latch_disable();
    busy_wait_us_32(CS_RELEASE_SETTLE_US);
    latch_load(LATCH_SAFE);
}
