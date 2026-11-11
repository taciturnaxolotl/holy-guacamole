#pragma once

/*
 * Host stand-in for the pico-sdk pico/stdlib.h, covering only the GPIO
 * and delay calls the IMU driver uses. Delays advance a simulated clock
 * instead of sleeping. See fake_pico.h.
 */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define GPIO_OUT 1
#define GPIO_IN  0

typedef enum { GPIO_FUNC_SPI = 1, GPIO_FUNC_SIO = 5 } gpio_function_t;

void gpio_init(unsigned int gpio);
void gpio_set_dir(unsigned int gpio, bool out);
void gpio_put(unsigned int gpio, bool value);
void gpio_set_function(unsigned int gpio, gpio_function_t fn);

void busy_wait_us_32(uint32_t delay_us);
void sleep_us(uint64_t us);
void sleep_ms(uint32_t ms);
