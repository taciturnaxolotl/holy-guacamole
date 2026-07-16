/*
 * Visual gamepad mapper for Radiomaster Zorro (and other EdgeTX radios).
 *
 * Reads raw HID via IOKit, displays all axes and buttons live,
 * and lets you interactively map them to meltybrain controls.
 * Outputs a C struct you can paste into the sim.
 *
 * Build (inside nix shell):
 *   cc -o mapper sim/zorro_mapper.c -framework IOKit -framework CoreFoundation \
 *      $(pkg-config --cflags --libs raylib) -lm
 *   ./mapper
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <IOKit/hid/IOHIDManager.h>
#include <IOKit/hid/IOHIDDevice.h>
#include <CoreFoundation/CoreFoundation.h>
#include "raylib.h"

#define TARGET_VENDOR  4617
#define TARGET_PRODUCT 20308
#define MAX_REPORT     64
#define NUM_AXES       8
#define NUM_BUTTONS    24

/* ── HID state (updated from callback) ────────────────────────────── */

static volatile uint8_t  hid_report[MAX_REPORT];
static volatile int      hid_report_len = 0;
static volatile int      hid_updated = 0;
static uint8_t           hid_baseline[MAX_REPORT];
static int               hid_baseline_set = 0;

/* Parsed axis/button state derived from report bytes. */
static float  axis_val[NUM_AXES];     /* normalized -1..+1 */
static int    button_state[NUM_BUTTONS]; /* 0 or 1 */

/* EdgeTX classic joystick format varies by firmware version.
 * We try 8-bit axes first (more common on newer EdgeTX), then fall back
 * to 16-bit. The raw hex dump at the bottom shows the truth. */
static void parse_report(const uint8_t *rpt, int len) {
    /* Byte 0 is usually report ID. Axes start at byte 1.
     * Try 8-bit axes: 8 bytes, each 0-255 centered at 128. */
    for (int i = 0; i < NUM_AXES && (1 + i) < len; i++) {
        uint8_t raw = rpt[1 + i];
        axis_val[i] = ((float)raw - 128.0f) / 128.0f;
        if (axis_val[i] > 1.0f) axis_val[i] = 1.0f;
        if (axis_val[i] < -1.0f) axis_val[i] = -1.0f;
    }
    /* Buttons: packed bits starting after axes.
     * With 8-bit axes that's byte 9 onward. */
    int btn_offset = 1 + NUM_AXES;  /* byte 9 if 8-bit axes */
    for (int b = 0; b < NUM_BUTTONS; b++) {
        int byte_idx = btn_offset + b / 8;
        int bit_idx = b % 8;
        if (byte_idx < len)
            button_state[b] = (rpt[byte_idx] >> bit_idx) & 1;
        else
            button_state[b] = 0;
    }
}

static void hid_callback(void *ctx, IOReturn result, void *sender,
                         IOHIDReportType type, uint32_t reportID,
                         uint8_t *report, CFIndex reportLength) {
    (void)ctx; (void)result; (void)sender; (void)type; (void)reportID;
    if (reportLength > MAX_REPORT) reportLength = MAX_REPORT;
    memcpy((void *)hid_report, report, reportLength);
    hid_report_len = (int)reportLength;
    hid_updated = 1;

    if (!hid_baseline_set) {
        memcpy(hid_baseline, report, reportLength);
        hid_baseline_set = 1;
    }
}

/* ── Mapping definitions ──────────────────────────────────────────── */

typedef enum {
    MAP_AXIS,
    MAP_BUTTON,
} map_type_t;

typedef struct {
    const char *name;
    map_type_t  type;
    int         index;      /* axis or button index, -1 = unmapped */
    float       scale;      /* for axes: multiplier (1.0 or -1.0 to invert) */
} mapping_t;

static mapping_t mappings[] = {
    { "Drift X (R-stick X)",    MAP_AXIS,   -1,  1.0f },
    { "Drift Y (R-stick Y)",    MAP_AXIS,   -1,  1.0f },
    { "Speed (L-stick Y)",      MAP_AXIS,   -1,  1.0f },
    { "Bearing (L-stick X)",    MAP_AXIS,   -1,  1.0f },
    { "Safety (SF switch)",     MAP_BUTTON, -1,  1.0f },
    { "Mode (SA switch)",       MAP_BUTTON, -1,  1.0f },
    { "Attack (SC button)",     MAP_BUTTON, -1,  1.0f },
    { "Spin dir (SD button)",   MAP_BUTTON, -1,  1.0f },
    { "Heading trim (L slider)",MAP_AXIS,   -1,  1.0f },
    { "Phase trim (R slider)",  MAP_AXIS,   -1,  1.0f },
};
#define NUM_MAPPINGS (sizeof(mappings) / sizeof(mappings[0]))

static int selected_mapping = 0;
static int binding_mode = 0;  /* 1 = waiting for input to bind */

/* ── Main ─────────────────────────────────────────────────────────── */

int main(void) {
    /* Set up HID. */
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
        fprintf(stderr, "HID open failed (0x%x). Is Zorro plugged in?\n", ret);
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

    static uint8_t report_buf[MAX_REPORT];
    IOHIDDeviceRegisterInputReportCallback(dev, report_buf, MAX_REPORT, hid_callback, NULL);
    IOHIDManagerScheduleWithRunLoop(mgr, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);

    printf("Zorro Mapper: Found device. Starting GUI...\n");

    /* Init raylib. */
    InitWindow(960, 700, "Zorro Mapper");
    SetTargetFPS(60);

    while (!WindowShouldClose()) {
        /* Process HID on the run loop (non-blocking). */
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.001, false);

        if (hid_updated) {
            parse_report((const uint8_t *)hid_report, hid_report_len);
            hid_updated = 0;

            /* Auto-bind: if in binding mode, find the most-changed axis or
             * any pressed button and assign it. */
            if (binding_mode) {
                /* Check buttons first. */
                for (int b = 0; b < NUM_BUTTONS; b++) {
                    if (button_state[b]) {
                        mappings[selected_mapping].type = MAP_BUTTON;
                        mappings[selected_mapping].index = b;
                        binding_mode = 0;
                        break;
                    }
                }
                /* If no button pressed, check axes for large deflection. */
                if (binding_mode) {
                    for (int a = 0; a < NUM_AXES; a++) {
                        if (fabsf(axis_val[a]) > 0.7f) {
                            mappings[selected_mapping].type = MAP_AXIS;
                            mappings[selected_mapping].index = a;
                            mappings[selected_mapping].scale = (axis_val[a] > 0) ? 1.0f : -1.0f;
                            binding_mode = 0;
                            break;
                        }
                    }
                }
            }
        }

        /* Keyboard navigation. */
        if (IsKeyPressed(KEY_UP))   { selected_mapping--; if (selected_mapping < 0) selected_mapping = NUM_MAPPINGS - 1; }
        if (IsKeyPressed(KEY_DOWN)) { selected_mapping++; if (selected_mapping >= (int)NUM_MAPPINGS) selected_mapping = 0; }
        if (IsKeyPressed(KEY_ENTER) || IsKeyPressed(KEY_SPACE)) { binding_mode = !binding_mode; }
        if (IsKeyPressed(KEY_BACKSPACE)) { mappings[selected_mapping].index = -1; }
        if (IsKeyPressed(KEY_I)) { mappings[selected_mapping].scale *= -1.0f; }

        /* Print mapping to console on P key. */
        if (IsKeyPressed(KEY_P)) {
            printf("\n/* Zorro mapping — paste into drive.c */\n");
            for (int i = 0; i < (int)NUM_MAPPINGS; i++) {
                if (mappings[i].index >= 0) {
                    if (mappings[i].type == MAP_AXIS)
                        printf("  // %s -> axis[%d] (scale %.0f)\n",
                               mappings[i].name, mappings[i].index, mappings[i].scale);
                    else
                        printf("  // %s -> button[%d]\n",
                               mappings[i].name, mappings[i].index);
                } else {
                    printf("  // %s -> UNMAPPED\n", mappings[i].name);
                }
            }
            printf("\n");
        }

        /* ── Render ── */
        BeginDrawing();
        ClearBackground((Color){18, 18, 24, 255});

        DrawText("ZORRO MAPPER", 20, 12, 22, (Color){240, 170, 40, 255});
        DrawText("Up/Down select  Enter bind  Backspace clear  I invert  P print",
                 20, 40, 13, (Color){120, 120, 140, 255});

        int y = 65;

        /* Mapping list. */
        for (int i = 0; i < (int)NUM_MAPPINGS; i++) {
            bool sel = (i == selected_mapping);
            Color bg = sel ? (Color){40, 50, 70, 255} : (Color){25, 25, 32, 255};
            DrawRectangle(15, y - 2, 440, 22, bg);

            char label[128];
            if (mappings[i].index < 0)
                snprintf(label, sizeof(label), "%s: [unmapped]", mappings[i].name);
            else if (mappings[i].type == MAP_AXIS)
                snprintf(label, sizeof(label), "%s: axis[%d]%s",
                         mappings[i].name, mappings[i].index,
                         mappings[i].scale < 0 ? " (inv)" : "");
            else
                snprintf(label, sizeof(label), "%s: button[%d]",
                         mappings[i].name, mappings[i].index);

            Color col = sel ? (Color){240, 220, 100, 255} : RAYWHITE;
            if (sel && binding_mode) col = (Color){100, 240, 140, 255};
            DrawText(label, 22, y + 2, 14, col);

            if (sel && binding_mode)
                DrawText("<< MOVE STICK OR PRESS BUTTON >>", 470, y + 2, 14,
                         (Color){100, 240, 140, 255});

            y += 24;
        }

        y += 15;

        /* Live axis display. */
        DrawText("RAW AXES:", 20, y, 14, (Color){160, 160, 180, 255});
        y += 18;
        for (int a = 0; a < NUM_AXES; a++) {
            float v = axis_val[a];
            int bar_x = 120, bar_w = 200, bar_cx = bar_x + bar_w / 2;
            DrawRectangle(bar_x, y, bar_w, 10, (Color){35, 35, 45, 255});
            DrawLine(bar_cx, y, bar_cx, y + 10, (Color){70, 70, 90, 255});
            int fill = (int)(v * bar_w / 2);
            Color acol = fabsf(v) > 0.7f ? (Color){240, 200, 80, 255}
                                         : (Color){100, 140, 180, 255};
            if (fill > 0) DrawRectangle(bar_cx, y, fill, 10, acol);
            else          DrawRectangle(bar_cx + fill, y, -fill, 10, acol);

            DrawText(TextFormat("Axis %d: %+.3f", a, (double)v), 20, y, 12, RAYWHITE);
            y += 14;
        }

        y += 10;

        /* Live button display. */
        DrawText("RAW BUTTONS:", 20, y, 14, (Color){160, 160, 180, 255});
        y += 18;
        int bx = 20;
        for (int b = 0; b < NUM_BUTTONS; b++) {
            Color bcol = button_state[b] ? (Color){120, 240, 140, 255}
                                         : (Color){60, 60, 80, 255};
            DrawCircle(bx + 8, y + 8, 7.0f, bcol);
            DrawText(TextFormat("%d", b), bx + 2, y + 20, 10, (Color){120, 120, 140, 255});
            bx += 36;
            if ((b + 1) % 12 == 0) { bx = 20; y += 32; }
        }

        y += 15;

        /* Raw hex dump of current report. */
        DrawText("RAW REPORT:", 20, y, 14, (Color){160, 160, 180, 255});
        y += 18;
        char hex[512] = {0};
        int hlen = hid_report_len;
        if (hlen > MAX_REPORT) hlen = MAX_REPORT;
        for (int i = 0; i < hlen; i++) {
            snprintf(hex + i * 3, 4, "%02x ", ((const uint8_t *)hid_report)[i]);
        }
        DrawText(hex, 20, y, 13, (Color){140, 180, 140, 255});
        y += 18;
        DrawText(TextFormat("Report length: %d bytes", hlen), 20, y, 12,
                 (Color){120, 120, 140, 255});

        EndDrawing();
    }

    CloseWindow();
    IOHIDManagerClose(mgr, kIOHIDOptionsTypeNone);
    CFRelease(mgr);
    printf("Done.\n");
    return 0;
}
