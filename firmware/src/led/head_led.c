#include "head_led.h"
#include "hw_pins.h"
#include "hardware/pio.h"
#include "hardware/timer.h"
#include "head_led.pio.h"
#include <math.h>
#include <stdbool.h>

/* Tunables. */
#define SPIN_OMEGA_MIN   10.0f     /* rad/s; below this the robot is "idle" */
#define REF_HEADING      0.0f      /* heading at which the dot appears */
#define STALE_US         200000u   /* no estimate for this long => idle */
#define STROBE_US        400u      /* spec window is 300-500 us */
#define STROBE_LEAD_US   2000u     /* queue a strobe this close to its start */

/* The PIO holds the pin low for 3x the on-time after each pulse. */
#define PULSE_CYCLE_US(on_us) (4u * (on_us))

/* `count` blinks of `on_ms`, starting every `on_ms + gap_ms`, repeated every
 * `period_ms`. Keep gap_ms >= 3 * on_ms so the PIO off-time never stretches
 * the pattern. */
typedef struct {
    uint16_t period_ms;
    uint8_t  count;
    uint16_t on_ms;
    uint16_t gap_ms;
} blink_pattern_t;

static const blink_pattern_t PATTERNS[] = {
    [HEAD_LED_NO_LINK]     = { 2000, 1,  50,   0 },
    [HEAD_LED_DISARMED]    = { 1000, 1,  50,   0 },
    [HEAD_LED_ARMED]       = { 1000, 2,  50, 150 },
    [HEAD_LED_LOW_BATTERY] = {  200, 1,  40,   0 },
    [HEAD_LED_FAILSAFE]    = { 1500, 3,  50, 150 },
    /* The spec's 1 s on / 1 s off is 50% duty, over the 25% cap. */
    [HEAD_LED_IMU_FAULT]   = { 2000, 1, 400,   0 },
};

static PIO      s_pio = pio1;
static uint     s_sm;
static bool     s_ok;

static head_led_status_t s_status;
static uint32_t s_period_start_us;
static uint8_t  s_blink_idx;
static uint32_t s_busy_until_us;

static float    s_heading;
static float    s_omega;
static uint32_t s_update_us;
static bool     s_have;

void head_led_init(void) {
    s_ok = false;
    s_have = false;
    s_status = HEAD_LED_NO_LINK;
    s_blink_idx = 0;
    s_busy_until_us = time_us_32();

    if (!pio_can_add_program(s_pio, &head_led_program)) return;
    int sm = pio_claim_unused_sm(s_pio, false);
    if (sm < 0) return;
    s_sm = (uint)sm;
    uint offset = pio_add_program(s_pio, &head_led_program);
    head_led_program_init(s_pio, s_sm, offset, PIN_HEAD_LED);
    pio_sm_set_enabled(s_pio, s_sm, true);
    s_ok = true;
}

static void pulse(uint32_t delay_us, uint32_t on_us) {
    uint32_t delay = delay_us / head_led_TICK_US;
    uint32_t on = on_us / head_led_TICK_US;
    /* The program's set instructions add 2 ticks to the on-time. */
    on = on > 2u ? on - 2u : 0u;
    if (delay > 0xFFFFu) delay = 0xFFFFu;
    if (on > 0xFFFFu) on = 0xFFFFu;
    pio_sm_put(s_pio, s_sm, (on << 16) | delay);
}

void head_led_set_status(head_led_status_t status) {
    if (status == s_status) return;
    s_status = status;
    s_blink_idx = 0;
}

void head_led_on_estimate(const heading_estimate_t *est, uint32_t now_us) {
    s_heading = est->heading;
    s_omega = est->omega;
    s_update_us = now_us;
    s_have = true;
}

static float wrap_2pi(float a) {
    const float two_pi = 2.0f * (float)M_PI;
    a = fmodf(a, two_pi);
    return a < 0.0f ? a + two_pi : a;
}

/* Signed difference so the 32-bit microsecond clock can wrap. */
static bool reached(uint32_t now_us, uint32_t t_us) {
    return (int32_t)(now_us - t_us) >= 0;
}

static void tick_strobe(uint32_t now_us) {
    if (!reached(now_us, s_busy_until_us)) return;

    /* Extrapolate heading to "now" so the dot stays put between the
     * (slower) estimate updates, then find how long until it sweeps past
     * the reference in the direction of rotation. */
    float dt = (float)(now_us - s_update_us) * 1e-6f;
    float heading = s_heading + s_omega * dt;
    float ang = s_omega > 0.0f ? wrap_2pi(REF_HEADING - heading)
                               : wrap_2pi(heading - REF_HEADING);
    float until_us = ang / fabsf(s_omega) * 1e6f - (float)(STROBE_US / 2u);
    if (until_us > (float)STROBE_LEAD_US) return;

    uint32_t delay_us = until_us > 0.0f ? (uint32_t)until_us : 0u;
    pulse(delay_us, STROBE_US);
    s_busy_until_us = now_us + delay_us + PULSE_CYCLE_US(STROBE_US);
}

static void tick_status(uint32_t now_us) {
    const blink_pattern_t *p = &PATTERNS[s_status];

    if (s_blink_idx >= p->count) {
        if (!reached(now_us, s_period_start_us + p->period_ms * 1000u)) return;
        s_blink_idx = 0;
    }
    if (s_blink_idx == 0) {
        if (!reached(now_us, s_busy_until_us)) return;
        s_period_start_us = now_us;
    }

    uint32_t start_us = s_period_start_us +
                        (uint32_t)s_blink_idx * (p->on_ms + p->gap_ms) * 1000u;
    if (!reached(now_us, start_us)) return;

    pulse(0, p->on_ms * 1000u);
    s_busy_until_us = now_us + PULSE_CYCLE_US(p->on_ms * 1000u);
    s_blink_idx++;
}

void head_led_tick(uint32_t now_us) {
    if (!s_ok) return;

    bool stale = !s_have || (now_us - s_update_us) > STALE_US;
    if (!stale && fabsf(s_omega) > SPIN_OMEGA_MIN) {
        tick_strobe(now_us);
        s_blink_idx = 0;
    } else {
        tick_status(now_us);
    }
}
