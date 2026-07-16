/*
 * RadioMaster Zorro gamepad reader for the SITL simulator.
 *
 * On macOS, raylib's gamepad API uses the GameController framework which
 * doesn't expose the Zorro's 8 EdgeTX axes properly. Instead we read the
 * raw 19-byte HID report via IOKit and parse it ourselves, using the
 * verified byte offsets from zorro_detect.c.
 *
 * Uses per-device callback registration (same approach as zorro_detect.c
 * which works). Re-scans for the device if not yet connected.
 */

#include "zorro_input.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <IOKit/hid/IOHIDManager.h>
#include <CoreFoundation/CoreFoundation.h>

#define TARGET_VENDOR   4617
#define TARGET_PRODUCT 20308
#define MAX_REPORT      64

static uint8_t g_report[MAX_REPORT];
static int     g_report_len = 0;
static bool    g_connected = false;
static bool    g_initialized = false;
static IOHIDManagerRef g_mgr = NULL;
static IOHIDDeviceRef  g_dev = NULL;
static bool g_callback_registered = false;

static void hid_callback(void *ctx, IOReturn result, void *sender,
                         IOHIDReportType type, uint32_t reportID,
                         uint8_t *report, CFIndex len) {
    (void)ctx; (void)result; (void)sender; (void)type; (void)reportID;
    if (len > MAX_REPORT) len = MAX_REPORT;
    memcpy(g_report, report, len);
    g_report_len = (int)len;
    g_connected = true;
}

static void zorro_hid_init(void) {
    if (g_initialized) return;

    g_mgr = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    if (!g_mgr) {
        fprintf(stderr, "zorro: IOHIDManagerCreate failed\n");
        return;
    }

    CFNumberRef vid = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType,
                                    &(int){TARGET_VENDOR});
    CFNumberRef pid = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType,
                                    &(int){TARGET_PRODUCT});
    CFMutableDictionaryRef match = CFDictionaryCreateMutable(
        kCFAllocatorDefault, 0,
        &kCFTypeDictionaryKeyCallBacks,
        &kCFTypeDictionaryValueCallBacks);
    CFDictionarySetValue(match, CFSTR(kIOHIDVendorIDKey), vid);
    CFDictionarySetValue(match, CFSTR(kIOHIDProductIDKey), pid);
    IOHIDManagerSetDeviceMatching(g_mgr, match);
    CFRelease(match); CFRelease(vid); CFRelease(pid);

    IOReturn ret = IOHIDManagerOpen(g_mgr, kIOHIDOptionsTypeNone);
    if (ret != kIOReturnSuccess) {
        fprintf(stderr, "zorro: HID open failed (0x%x)\n", ret);
        CFRelease(g_mgr);
        g_mgr = NULL;
        return;
    }

    IOHIDManagerScheduleWithRunLoop(g_mgr,
                                    CFRunLoopGetCurrent(),
                                    kCFRunLoopDefaultMode);
    g_initialized = true;
    fprintf(stderr, "zorro: HID manager initialized, scanning for device...\n");
}

static void zorro_try_connect(void) {
    if (g_callback_registered) return;

    CFSetRef devices = IOHIDManagerCopyDevices(g_mgr);
    if (!devices || CFSetGetCount(devices) == 0) {
        if (devices) CFRelease(devices);
        return;
    }

    const void *dev_ptr = NULL;
    CFSetGetValues(devices, &dev_ptr);
    g_dev = (IOHIDDeviceRef)dev_ptr;
    CFRelease(devices);

    static uint8_t rpt_buf[MAX_REPORT];
    IOHIDDeviceRegisterInputReportCallback(g_dev, rpt_buf, MAX_REPORT,
                                            hid_callback, NULL);
    IOHIDDeviceScheduleWithRunLoop(g_dev,
                                   CFRunLoopGetCurrent(),
                                   kCFRunLoopDefaultMode);
    g_callback_registered = true;
    fprintf(stderr, "zorro: device found, callback registered\n");
}

static int read16(const uint8_t *rpt, int byte_idx) {
    if (byte_idx + 1 >= g_report_len) return 0;
    return (int)rpt[byte_idx] | ((int)rpt[byte_idx + 1] << 8);
}

static float axis_to_float(int raw) {
    float v = (float)(raw - 1024) / 1024.0f;
    if (v > 1.0f) v = 1.0f;
    if (v < -1.0f) v = -1.0f;
    return v;
}

static float deadband(float v, float threshold) {
    if (fabsf(v) < threshold) return 0.0f;
    return v;
}

zorro_input_t zorro_read(void) {
    zorro_input_t z = {0};

    if (!g_initialized) zorro_hid_init();
    if (!g_initialized) return z;

    /* Re-scan for the device each frame until we find it. */
    if (!g_callback_registered) zorro_try_connect();
    if (!g_callback_registered) return z;

    /* Pump the CFRunLoop to process pending HID reports.
     * 10ms gives IOKit enough time to deliver reports even
     * when raylib's GLFW event processing is competing. */
    CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.010, false);

    z.gamepad_present = g_connected && g_report_len >= 19;
    if (!z.gamepad_present) return z;

    z.rstick_x = deadband(axis_to_float(read16(g_report, 3)),
                          ZORRO_STICK_DEADBAND);
    z.rstick_y = deadband(axis_to_float(read16(g_report, 5)),
                          ZORRO_STICK_DEADBAND);
    z.lstick_y = deadband(axis_to_float(read16(g_report, 7)),
                          ZORRO_STICK_DEADBAND);
    z.lstick_x = deadband(axis_to_float(read16(g_report, 9)),
                          ZORRO_STICK_DEADBAND);

    z.se_switch = axis_to_float(read16(g_report, 11));
    z.sf_switch = axis_to_float(read16(g_report, 13));
    z.sb_switch = axis_to_float(read16(g_report, 15));
    z.sc_switch = axis_to_float(read16(g_report, 17));

    /* Buttons are packed into byte 0 of the 19-byte report.
     * From zorro_detect: byte 0 = 0x20 at rest (bit 5 = S2 knob position).
     * Button 1 (left top, SA) = bit 0, etc. */
    if (g_report_len > 0) {
        uint8_t btn_byte = g_report[0];
        z.sa_pressed = (btn_byte >> 0) & 1;
        z.sd_pressed = (btn_byte >> 1) & 1;
        z.sg_pressed = (btn_byte >> 2) & 1;
        z.sh_pressed = (btn_byte >> 3) & 1;
        z.s1_pressed = (btn_byte >> 4) & 1;
        z.s2_pressed = (btn_byte >> 5) & 1;
    }

    return z;
}

void zorro_debug_dump(const zorro_input_t *z) {
    if (!z->gamepad_present) {
        printf("Zorro: NOT CONNECTED\n");
        return;
    }
    printf("Zorro: L(%.2f, %.2f) R(%.2f, %.2f) "
           "SE %.2f SF %.2f SB %.2f SC %.2f "
           "SA:%d SD:%d SG:%d SH:%d S1:%d S2:%d\n",
           (double)z->lstick_x, (double)z->lstick_y,
           (double)z->rstick_x, (double)z->rstick_y,
           (double)z->se_switch, (double)z->sf_switch,
           (double)z->sb_switch, (double)z->sc_switch,
           z->sa_pressed, z->sd_pressed,
           z->sg_pressed, z->sh_pressed,
           z->s1_pressed, z->s2_pressed);
}
