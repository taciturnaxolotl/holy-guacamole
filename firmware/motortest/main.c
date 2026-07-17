/*
 * Motor + channel bench test for the XIAO RP2350.
 *
 * TEMPORARY tool image, not the flight controller. It lets you spin each
 * ESC/motor independently at a low, capped throttle and watch the raw CRSF
 * channel values, so you can verify wiring before trusting the real
 * spin-control firmware. Restore the flight firmware when done:
 *   picotool load -x -f build/holy_guacamole.uf2
 *
 * ┌───────────────────────── SAFETY ─────────────────────────┐
 * │ REMOVE THE WEAPON BLADE. Get the wheels off the bench     │
 * │ (prop the robot up) so it can't drive itself off the      │
 * │ edge. Throttle is capped low but motors still move.       │
 * └───────────────────────────────────────────────────────────┘
 *
 * Drive it from a serial terminal that sends keys live (screen, not cat):
 *   screen /dev/cu.usbmodemXXXX 115200
 *
 * Keys:
 *   a : spin motor A (DSHOT1, GPIO6) at the cap
 *   b : spin motor B (DSHOT2, GPIO7) at the cap
 *   c : spin both
 *   s / space : stop
 *   1..5 : set throttle cap to 5/10/15/20/25 %
 *   + / - : nudge cap up/down
 *
 * Any running motor auto-stops after SPIN_TIMEOUT_MS as a dead-man.
 */

#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "dshot.h"
#include "crsf.h"
#include "hw_pins.h"

#define SPIN_TIMEOUT_MS  8000   /* auto-stop a running motor after this */
#define CAP_DEFAULT      0.10f
#define CAP_MAX          0.30f
#define CAP_STEP         0.05f

static float thr_a, thr_b;      /* commanded throttle fractions */
static float cap = CAP_DEFAULT;
static uint32_t last_cmd_ms;

static void stop(void) { thr_a = 0.0f; thr_b = 0.0f; }

static void apply_key(int ch) {
    switch (ch) {
        case 'a': thr_a = cap; thr_b = 0.0f; break;
        case 'b': thr_b = cap; thr_a = 0.0f; break;
        case 'c': thr_a = cap; thr_b = cap; break;
        case 's': case ' ': stop(); break;
        case '+': cap += CAP_STEP; break;
        case '-': cap -= CAP_STEP; break;
        case '1': cap = 0.05f; break;
        case '2': cap = 0.10f; break;
        case '3': cap = 0.15f; break;
        case '4': cap = 0.20f; break;
        case '5': cap = 0.25f; break;
        default: return;
    }
    if (cap < 0.0f) cap = 0.0f;
    if (cap > CAP_MAX) cap = CAP_MAX;
    /* Re-apply the cap to whatever is already spinning. */
    if (thr_a > 0.0f) thr_a = cap;
    if (thr_b > 0.0f) thr_b = cap;
    last_cmd_ms = to_ms_since_boot(get_absolute_time());
    printf("\n>> cap=%.0f%%  A=%.0f%%  B=%.0f%%\n",
           (double)(cap * 100), (double)(thr_a * 100), (double)(thr_b * 100));
}

int main(void) {
    stdio_init_all();
    sleep_ms(2000);   /* let USB CDC enumerate before the banner */

    printf("\n=== Motor + channel bench test ===\n");
    printf("SAFETY: remove the weapon blade, wheels off the bench.\n");
    printf("keys: a=motorA b=motorB c=both s/space=stop 1-5=cap +/-=nudge\n\n");

    dshot_esc_t esc1, esc2;
    if (!dshot_load_program(pio0)) printf("PIO load failed\n");
    if (!dshot_init(&esc1, pio0, PIN_DSHOT1)) printf("DSHOT1 init failed\n");
    if (!dshot_init(&esc2, pio0, PIN_DSHOT2)) printf("DSHOT2 init failed\n");
    crsf_init();
    crsf_state_t rc = {0};

    /* Arm the ESCs: stream zero throttle for a couple seconds. */
    for (int i = 0; i < 2000; i++) {
        dshot_set_throttle(&esc1, 0.0f);
        dshot_set_throttle(&esc2, 0.0f);
        sleep_ms(1);
    }
    printf("ESCs armed (zero throttle sent). Ready.\n");

    last_cmd_ms = to_ms_since_boot(get_absolute_time());
    uint32_t last_print = 0;

    while (1) {
        int ch = getchar_timeout_us(0);
        if (ch != PICO_ERROR_TIMEOUT) apply_key(ch);

        uint32_t now = to_ms_since_boot(get_absolute_time());

        /* Dead-man: stop after inactivity if anything is spinning. */
        if ((thr_a > 0.0f || thr_b > 0.0f) &&
            (now - last_cmd_ms) > SPIN_TIMEOUT_MS) {
            stop();
            printf("\n>> auto-stop (%.1fs timeout)\n", SPIN_TIMEOUT_MS / 1000.0);
        }

        /* DSHOT must be refreshed continuously (>200 Hz). */
        dshot_set_throttle(&esc1, thr_a);
        dshot_set_throttle(&esc2, thr_b);
        dshot_read_telemetry(&esc1);
        dshot_read_telemetry(&esc2);

        crsf_poll(&rc);

        if (now - last_print > 250) {
            last_print = now;
            printf("A=%3.0f%% (rpm %5lu)  B=%3.0f%% (rpm %5lu) | "
                   "ch: %4u %4u %4u %4u %4u %4u %s\n",
                   (double)(thr_a * 100), (unsigned long)esc1.telemetry.rpm,
                   (double)(thr_b * 100), (unsigned long)esc2.telemetry.rpm,
                   rc.channels[0], rc.channels[1], rc.channels[2],
                   rc.channels[3], rc.channels[4], rc.channels[5],
                   crsf_link_alive(&rc, 500) ? "RC-OK" : "no-rc");
        }

        sleep_us(500);   /* ~2 kHz loop */
    }
}
