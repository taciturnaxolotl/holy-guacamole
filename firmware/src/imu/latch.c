#include "latch.h"
#include "hw_pins.h"

#include "hardware/spi.h"
#include "pico/stdlib.h"

static uint8_t latch_shadow = LATCH_SAFE;

void latch_init(void) {
    gpio_init(PIN_SEL_OE_N);
    gpio_set_dir(PIN_SEL_OE_N, GPIO_OUT);
    gpio_put(PIN_SEL_OE_N, 1);  /* start blanked (outputs high-Z) */

    gpio_init(PIN_SEL_LAT);
    gpio_set_dir(PIN_SEL_LAT, GPIO_OUT);
    gpio_put(PIN_SEL_LAT, 0);   /* start low */
}

void latch_load(uint8_t image) {
    /* Shift the byte out on SPI MOSI/SCK.
     * SN74HC595 shifts MSB-first into QA...QH, so the last bit
     * shifted in ends up at QA. Our convention: QA=bit0 (CS_A).
     * Bit-reverse so that our bit0 lands at QA after 8 clocks. */
    uint8_t reversed = 0;
    for (int i = 0; i < 8; i++) {
        if (image & (1 << i)) reversed |= (1 << (7 - i));
    }
    spi_write_blocking(SPI_INST, &reversed, 1);

    /* Pulse SEL_LAT to transfer shift register to output latch */
    gpio_put(PIN_SEL_LAT, 1);
    busy_wait_us_32(1);
    gpio_put(PIN_SEL_LAT, 0);

    latch_shadow = image;
}

void latch_enable(void) {
    gpio_put(PIN_SEL_OE_N, 0);
}

void latch_disable(void) {
    gpio_put(PIN_SEL_OE_N, 1);
}

void latch_select(uint8_t bit) {
    latch_disable();
    uint8_t image = LATCH_SAFE;
    image &= ~(1 << bit);
    latch_load(image);
    latch_enable();
}

void latch_deselect_all(void) {
    latch_disable();
    latch_load(LATCH_SAFE);
}

static uint8_t latch_get_image(void) {
    return latch_shadow;
}
