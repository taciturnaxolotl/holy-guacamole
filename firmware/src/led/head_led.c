#include "head_led.h"
#include "hw_pins.h"
#include "hardware/gpio.h"
#include <math.h>

/* Tunables. */
#define SPIN_OMEGA_MIN   10.0f     /* rad/s; below this the robot is "idle" */
#define STROBE_WINDOW    0.35f     /* rad (~20 deg) total width of the dot */
#define REF_HEADING      0.0f      /* heading at which the dot appears */
#define STALE_US         200000u   /* no estimate for this long => idle */
#define IDLE_BLINK_US    250000u   /* idle heartbeat half-period (2 Hz) */

static float    s_heading;
static float    s_omega;
static uint32_t s_update_us;
static bool     s_have;

void head_led_init(void) {
    gpio_init(PIN_HEAD_LED);
    gpio_set_dir(PIN_HEAD_LED, GPIO_OUT);
    gpio_put(PIN_HEAD_LED, 0);
    s_have = false;
}

void head_led_on_estimate(const heading_estimate_t *est, uint32_t now_us) {
    s_heading = est->heading;
    s_omega = est->omega;
    s_update_us = now_us;
    s_have = true;
}

static float wrap_pi(float a) {
    const float pi = (float)M_PI;
    while (a >= pi)  a -= 2.0f * pi;
    while (a < -pi)  a += 2.0f * pi;
    return a;
}

void head_led_tick(uint32_t now_us) {
    bool stale = !s_have || (now_us - s_update_us) > STALE_US;

    if (!stale && fabsf(s_omega) > SPIN_OMEGA_MIN) {
        /* Extrapolate heading to "now" so the dot stays put between the
         * (slower) estimate updates, then light the LED within a small
         * angular window around the reference heading. */
        float dt = (float)(now_us - s_update_us) * 1e-6f;
        float err = wrap_pi(s_heading + s_omega * dt - REF_HEADING);
        gpio_put(PIN_HEAD_LED, fabsf(err) < (STROBE_WINDOW * 0.5f));
    } else {
        /* Idle heartbeat. */
        gpio_put(PIN_HEAD_LED, ((now_us / IDLE_BLINK_US) & 1u) == 0u);
    }
}
