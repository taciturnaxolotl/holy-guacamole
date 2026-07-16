/*
 * Zorro HID mapper v5 — live ASCII visualization.
 *
 * Shows all 8 axes as live bar graphs and all buttons as indicators.
 * You see exactly what's moving in real time, then confirm each mapping.
 *
 * Build (inside nix shell):
 *   cmake -B build-sim -S sim && cmake --build build-sim --target zorro_detect
 *   ./build-sim/zorro_detect
 *
 * Axis layout verified against EdgeTX classic USB joystick mode:
 *   EdgeTX maps channelOutputs[0..7] to 8 HID axes (16-bit LE at bytes 3..17).
 *   The model's mixData determines which physical control feeds each channel.
 *
 *   For model05.yml (AETR, mode 2):
 *     axis 0 (byte 3)  = CH0 = I3(Ail) = Left stick X
 *     axis 1 (byte 5)  = CH1 = I1(Ele) = Right stick Y
 *     axis 2 (byte 7)  = CH2 = I2(Thr) = Left stick Y
 *     axis 3 (byte 9)  = CH3 = I0(Rud) = Right stick X
 *     axis 4 (byte 11) = CH4 = SE switch (3-pos)
 *     axis 5 (byte 13) = CH5 = SF switch (2-pos safety)
 *     axis 6 (byte 15) = CH6 = SB switch (3-pos)
 *     axis 7 (byte 17) = CH7 = SC switch (3-pos)
 *
 *   S1/S2 knobs are on CH12/CH13 → button bits, not analog axes.
 *   The Zorro has no sliders. Axes 4-7 carry switches, not pots.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <IOKit/hid/IOHIDManager.h>
#include <IOKit/hid/IOHIDDevice.h>
#include <CoreFoundation/CoreFoundation.h>

#define TARGET_VENDOR  4617
#define TARGET_PRODUCT 20308
#define MAX_REPORT     64
#define BAR_WIDTH      40
#define NUM_AXES       8
#define NUM_BUTTONS    24

static volatile uint8_t current_report[MAX_REPORT];
static volatile int     current_len = 0;
static volatile int     got_report = 0;

static void hid_cb(void *ctx, IOReturn result, void *sender,
                   IOHIDReportType type, uint32_t reportID,
                   uint8_t *report, CFIndex len) {
    (void)ctx; (void)result; (void)sender; (void)type; (void)reportID;
    if (len > MAX_REPORT) len = MAX_REPORT;
    memcpy((void *)current_report, report, len);
    current_len = (int)len;
    got_report = 1;
}

static bool wait_report(IOHIDManagerRef mgr, int timeout_ms) {
    got_report = 0;
    for (int i = 0; i < timeout_ms; i++) {
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.001, false);
        if (got_report) return true;
    }
    return false;
}

static int read16(int byte_idx) {
    if (byte_idx + 1 >= current_len) return 0;
    return (int)current_report[byte_idx] | ((int)current_report[byte_idx + 1] << 8);
}

/* ANSI escape helpers. */
#define ESC_HOME    "\033[H"
#define ESC_CLEAR   "\033[2J"
#define ESC_HIDE    "\033[?25l"
#define ESC_SHOW    "\033[?25h"
#define GREEN       "\033[32m"
#define YELLOW      "\033[33m"
#define RED         "\033[31m"
#define CYAN        "\033[36m"
#define DIM         "\033[2m"
#define BOLD        "\033[1m"
#define RESET       "\033[0m"

/* Axis labels matching model05.yml EdgeTX channel mapping (AETR mode 2).
 * Axes 4-7 are switches, not knobs/sliders. The Zorro has no sliders. */
static const char *axis_names[NUM_AXES] = {
    "L-Stick X", "R-Stick Y", "L-Stick Y", "R-Stick X",
    "SE Sw",    "SF Sw",    "SB Sw",    "SC Sw",
};

/* Axis byte offsets (EdgeTX classic joystick format). */
static const int axis_bytes[NUM_AXES] = { 3, 5, 7, 9, 11, 13, 15, 17 };

static void draw_bars(void) {
    printf(ESC_HOME);
    printf(BOLD "ZORRO LIVE MONITOR" RESET "  (Ctrl+C to quit)\n\n");

    /* Axes. */
    for (int a = 0; a < NUM_AXES; a++) {
        int raw = read16(axis_bytes[a]);
        float norm = ((float)raw - 1024.0f) / 1024.0f;
        if (norm > 1.0f) norm = 1.0f;
        if (norm < -1.0f) norm = -1.0f;

        int center = BAR_WIDTH / 2;
        int fill = (int)(norm * center);

        char bar[BAR_WIDTH + 1];
        memset(bar, ' ', BAR_WIDTH);
        bar[BAR_WIDTH] = '\0';
        bar[center] = '|';

        if (fill > 0) {
            for (int i = center + 1; i <= center + fill && i < BAR_WIDTH; i++)
                bar[i] = '#';
        } else {
            for (int i = center + fill; i < center && i >= 0; i++)
                bar[i] = '#';
        }

        const char *col = (fabsf(norm) > 0.7f) ? GREEN : DIM;
        printf("  %-11s [%s%s%s] %4d (%+.2f)\n",
               axis_names[a], col, bar, RESET, raw, (double)norm);
    }

    printf("\n");

    /* Buttons. */
    printf("  BUTTONS: ");
    for (int b = 0; b < NUM_BUTTONS && b < current_len * 8; b++) {
        int byte_idx = 19 + b / 8;  /* buttons start after axes */
        if (byte_idx >= current_len) byte_idx = b / 8;  /* fallback */
        int bit = b % 8;
        int pressed = 0;
        if (byte_idx < current_len)
            pressed = (current_report[byte_idx] >> bit) & 1;
        printf("%s%d%s", pressed ? BOLD GREEN : DIM, b, RESET);
        if ((b + 1) % 8 == 0) printf(" ");
    }
    printf("\n\n");

    /* Raw hex. */
    printf("  HEX: ");
    for (int i = 0; i < current_len; i++) {
        /* Highlight non-zero bytes. */
        if (current_report[i] != 0)
            printf(GREEN "%02x " RESET, current_report[i]);
        else
            printf(DIM "00 " RESET);
    }
    printf("\n");
}

/* Interactive verification: show live bars, ask user to move one axis. */
static int verify_axis_live(IOHIDManagerRef mgr, int axis_idx) {
    printf(ESC_CLEAR ESC_HIDE);
    printf(BOLD "\n>>> VERIFY: %s (byte[%d-%d]) <<<\n\n" RESET,
           axis_names[axis_idx], axis_bytes[axis_idx], axis_bytes[axis_idx] + 1);
    printf("Move ONLY this control. Watch the bars below.\n");
    printf("When the correct bar moves, press Enter to confirm.\n");
    printf("Press 's' + Enter to skip.\n\n");

    /* Live display loop. */
    while (1) {
        if (wait_report(mgr, 30)) {
            draw_bars();
        }
        /* Non-blocking stdin check. */
        fd_set fds;
        struct timeval tv = {0, 16000};  /* ~60fps refresh even without HID updates */
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        if (select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv) > 0) {
            char buf[16];
            if (fgets(buf, sizeof(buf), stdin)) {
                if (buf[0] == 's' || buf[0] == 'S') return -1;
                return axis_bytes[axis_idx];  /* confirmed */
            }
        }
    }
}

static int detect_button_live(IOHIDManagerRef mgr, const char *name) {
    printf(ESC_CLEAR ESC_HIDE);
    printf(BOLD "\n>>> DETECT: %s <<<\n\n" RESET, name);
    printf("Leave unpressed. Press Enter when ready...\n");
    fflush(stdout);
    getchar();

    /* Capture baseline. */
    wait_report(mgr, 100);
    uint8_t baseline[MAX_REPORT];
    memcpy(baseline, (const void *)current_report, current_len);

    printf(ESC_CLEAR ESC_HIDE);
    printf(BOLD "\n>>> PRESS AND HOLD: %s <<<\n\n" RESET, name);
    printf("Hold it now. Watching for changes...\n\n");

    /* Live display showing which bits changed. */
    int found_byte = -1, found_bit = -1;
    int watch_count = 0;
    while (watch_count < 500) {
        if (wait_report(mgr, 30)) {
            watch_count++;
            printf(ESC_HOME);
            printf(BOLD ">>> PRESSING: %s <<<\n\n" RESET, name);

            /* Show changed bits. */
            int changes = 0;
            for (int i = 0; i < current_len; i++) {
                uint8_t diff = baseline[i] ^ current_report[i];
                if (diff == 0) continue;
                for (int b = 0; b < 8; b++) {
                    if ((diff >> b) & 1) {
                        printf(GREEN "  ★ byte[%d] bit %d CHANGED" RESET
                               " (was %d, now %d)\n",
                               i, b,
                               (baseline[i] >> b) & 1,
                               (current_report[i] >> b) & 1);
                        if (found_byte < 0) {
                            found_byte = i;
                            found_bit = b;
                        }
                        changes++;
                    }
                }
            }
            if (changes == 0) printf(DIM "  (no changes yet...)\n" RESET);

            printf("\n  HEX diff: ");
            for (int i = 0; i < current_len; i++) {
                uint8_t diff = baseline[i] ^ current_report[i];
                if (diff) printf(YELLOW "%02x " RESET, diff);
                else printf(DIM "00 " RESET);
            }
            printf("\n\nPress Enter to confirm, 's'+Enter to skip.\n");
        }

        fd_set fds;
        struct timeval tv = {0, 16000};
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        if (select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv) > 0) {
            char buf[16];
            if (fgets(buf, sizeof(buf), stdin)) {
                if (buf[0] == 's' || buf[0] == 'S') return -1;
                if (found_byte >= 0) {
                    printf("  ✓ Confirmed: byte[%d] bit %d\n", found_byte, found_bit);
                    /* Store in our button arrays. */
                    return found_byte * 8 + found_bit;  /* encode as single int */
                }
                printf("  No change detected yet. Keep holding or 's' to skip.\n");
            }
        }
    }
    return -1;
}

int main(void) {
    printf("=== Zorro Mapper v4 ===\n\n");

    IOHIDManagerRef mgr = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    CFNumberRef vid = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &(int){TARGET_VENDOR});
    CFNumberRef pid = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &(int){TARGET_PRODUCT});
    CFMutableDictionaryRef match = CFDictionaryCreateMutable(
        kCFAllocatorDefault, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFDictionarySetValue(match, CFSTR(kIOHIDVendorIDKey), vid);
    CFDictionarySetValue(match, CFSTR(kIOHIDProductIDKey), pid);
    IOHIDManagerSetDeviceMatching(mgr, match);
    CFRelease(match); CFRelease(vid); CFRelease(pid);

    IOReturn ret = IOHIDManagerOpen(mgr, kIOHIDOptionsTypeNone);
    if (ret != kIOReturnSuccess) {
        fprintf(stderr, "HID open failed. Is Zorro plugged in?\n");
        return 1;
    }

    CFSetRef devices = IOHIDManagerCopyDevices(mgr);
    if (!devices || CFSetGetCount(devices) == 0) {
        fprintf(stderr, "No Zorro found.\n");
        return 1;
    }
    const void *dev_ptr = NULL;
    CFSetGetValues(devices, &dev_ptr);
    IOHIDDeviceRef dev = (IOHIDDeviceRef)dev_ptr;

    static uint8_t rpt_buf[MAX_REPORT];
    IOHIDDeviceRegisterInputReportCallback(dev, rpt_buf, MAX_REPORT, hid_cb, NULL);
    IOHIDManagerScheduleWithRunLoop(mgr, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);

    printf("Waiting for Zorro... ");
    fflush(stdout);
    if (!wait_report(mgr, 2000)) {
        fprintf(stderr, "Timeout.\n");
        return 1;
    }
    printf("OK! (%d bytes)\n\n", current_len);

    /* First, show live monitor so user can explore. */
    printf("Starting live monitor. Move sticks/buttons to explore.\n");
    printf("Press Enter when ready to begin mapping...\n\n");

    /* Quick live preview. */
    int preview_frames = 0;
    while (preview_frames < 300) {
        if (wait_report(mgr, 30)) {
            draw_bars();
            preview_frames++;
        }
        fd_set fds;
        struct timeval tv = {0, 16000};
        FD_ZERO(&fds);
        FD_SET(STDIN_FILENO, &fds);
        if (select(STDIN_FILENO + 1, &fds, NULL, NULL, &tv) > 0) {
            char buf[16];
            if (fgets(buf, sizeof(buf), stdin)) break;
        }
    }

    /* Verify each axis. */
    int verified_axis_bytes[NUM_AXES];
    for (int i = 0; i < NUM_AXES; i++) {
        verified_axis_bytes[i] = verify_axis_live(mgr, i);
    }

    /* Detect buttons. */
    const char *btn_names[] = {
        "SA Switch (Mode)", "SD Switch (Spin Dir)",
        "SG Switch", "SH Switch",
        "S1 Knob (left)", "S2 Knob (right)",
    };
    int num_btn_map = 6;
    int btn_encoded[6];

    for (int i = 0; i < num_btn_map; i++) {
        btn_encoded[i] = detect_button_live(mgr, btn_names[i]);
    }

    /* Restore terminal. */
    printf(ESC_CLEAR ESC_SHOW);

    /* Output C code. */
    printf("\n========================================\n");
    printf("MAPPING RESULTS — paste into drive.c\n");
    printf("========================================\n\n");

    printf("/* Verified axis byte offsets */\n");
    printf("static const int zorro_axis_bytes[%d] = {", NUM_AXES);
    for (int i = 0; i < NUM_AXES; i++) {
        int b = verified_axis_bytes[i] >= 0 ? verified_axis_bytes[i] : axis_bytes[i];
        printf("%s%d", i ? ", " : "", b);
    }
    printf("};\n\n");

    printf("/* Button byte+bit encoding: byte = val/8, bit = val%%8 */\n");
    printf("static const int zorro_btn_encoded[%d] = {", num_btn_map);
    for (int i = 0; i < num_btn_map; i++)
        printf("%s%d", i ? ", " : "", btn_encoded[i]);
    printf("};\n\n");

    printf("static float zorro_read_axis(const uint8_t *rpt, int idx) {\n");
    printf("    int raw = rpt[zorro_axis_bytes[idx]] |\n");
    printf("              (rpt[zorro_axis_bytes[idx] + 1] << 8);\n");
    printf("    float v = (float)(raw - 1024) / 1024.0f;\n");
    printf("    if (v > 1.0f) v = 1.0f;\n");
    printf("    if (v < -1.0f) v = -1.0f;\n");
    printf("    return v;\n");
    printf("}\n\n");

    printf("static int zorro_read_btn(const uint8_t *rpt, int idx) {\n");
    printf("    int enc = zorro_btn_encoded[idx];\n");
    printf("    if (enc < 0) return 0;\n");
    printf("    return (rpt[enc / 8] >> (enc %% 8)) & 1;\n");
    printf("}\n");

    printf("\nDone.\n");
    IOHIDManagerClose(mgr, kIOHIDOptionsTypeNone);
    CFRelease(mgr);
    return 0;
}
