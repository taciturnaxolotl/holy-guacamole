#include "battery.h"

#include "hw_pins.h"
#include "hardware/adc.h"

/* VBAT divider: R9=120k high, R10=33.2k low.
 * Pack voltage = adc_v * (120 + 33.2) / 33.2 = adc_v * 4.614 */
#define DIVIDER_RATIO 4.614f

/* ADC reference voltage on RP2350. */
#define ADC_VREF 3.3f

/* EMA filter coefficient. Lower = smoother but slower to respond.
 * At 1kHz sampling, alpha=0.01 gives ~100ms time constant. */
#define FILTER_ALPHA 0.01f

static float filtered_pack_v = 0.0f;
static bool initialized = false;

void battery_init(void) {
    adc_init();
    adc_gpio_init(PIN_VBAT_ADC);
    adc_select_input(ADC_VBAT_CHAN);
    /* Prime the filter with an initial reading. */
    uint16_t raw = adc_read();
    filtered_pack_v = (float)raw / 4095.0f * ADC_VREF * DIVIDER_RATIO;
    initialized = true;
}

void battery_sample(void) {
    if (!initialized) return;
    adc_select_input(ADC_VBAT_CHAN);
    uint16_t raw = adc_read();
    float pack_v = (float)raw / 4095.0f * ADC_VREF * DIVIDER_RATIO;
    filtered_pack_v += FILTER_ALPHA * (pack_v - filtered_pack_v);
}

bool battery_ok(void) {
    return battery_cell_voltage() >= BATTERY_HALT_V;
}

bool battery_low(void) {
    return battery_cell_voltage() < BATTERY_WARN_V;
}

float battery_voltage(void) {
    return filtered_pack_v;
}

float battery_cell_voltage(void) {
    return filtered_pack_v / (float)BATTERY_CELLS;
}
