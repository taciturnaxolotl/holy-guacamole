/*
 * CRSF channel monitor for the XIAO RP2350.
 *
 * TEMPORARY debug image. Prints all 16 RC channels live so you can assign
 * sticks/switches on the transmitter and see exactly which channel each one
 * lands on. Wiggle a control and watch for the "<= moving" marker.
 *
 * View it in a terminal that handles ANSI (screen refreshes in place):
 *   screen /dev/cu.usbmodemXXXX 115200
 *
 * Restore the flight firmware when done:
 *   picotool load -x -f build/holy_guacamole.uf2
 */

#include <stdio.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include "crsf.h"
#include "hw_pins.h"

/* CRSF stick/switch range. */
#define CH_MIN   172
#define CH_MID   992
#define CH_MAX   1811

/* Channels the flight firmware currently reads (for reference in the view).
 * Everything else is free to assign. */
static const char *role_of(int ch) {
    switch (ch) {
        case 0: return "stick X (roll)";
        case 1: return "stick Y (pitch)";
        case 2: return "throttle / base";
        default: return "";
    }
}

static const char *pos_label(uint16_t v) {
    if (v < 400)  return "LOW ";
    if (v > 1600) return "HIGH";
    if (abs((int)v - CH_MID) < 120) return "MID ";
    return "--  ";
}

int main(void) {
    stdio_init_all();
    sleep_ms(2000);

    crsf_init();
    crsf_state_t rc = {0};

    uint16_t prev[CRSF_NUM_CHANNELS] = {0};
    uint32_t moved_ms[CRSF_NUM_CHANNELS] = {0};

    uint32_t last_draw = 0;
    while (1) {
        crsf_poll(&rc);
        uint32_t now = to_ms_since_boot(get_absolute_time());

        /* Track which channels changed recently. */
        for (int i = 0; i < CRSF_NUM_CHANNELS; i++) {
            if (abs((int)rc.channels[i] - (int)prev[i]) > 25) moved_ms[i] = now;
            prev[i] = rc.channels[i];
        }

        if (now - last_draw < 66) continue;   /* ~15 Hz redraw */
        last_draw = now;

        printf("\033[2J\033[H");   /* clear + home */
        printf("CRSF channel monitor    link=%s\r\n",
               crsf_link_alive(&rc, 500) ? "OK" : "--");
        printf("wiggle a control; it shows \"<= moving\"\r\n\r\n");
        printf(" ch   raw   norm   pos            role\r\n");

        for (int i = 0; i < CRSF_NUM_CHANNELS; i++) {
            uint16_t v = rc.channels[i];
            int norm = ((int)v - CH_MID) * 100 / (CH_MAX - CH_MID);
            if (norm > 100) norm = 100;
            if (norm < -100) norm = -100;
            bool moving = (now - moved_ms[i]) < 800;
            printf(" %2d  %4u  %+4d%%  %s   %-16s%s\r\n",
                   i + 1, v, norm, pos_label(v), role_of(i),
                   moving ? "<= moving" : "");
        }

        sleep_ms(5);
    }
}
