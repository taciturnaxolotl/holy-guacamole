/*
 * Raw HID report dumper for generating SDL2 gamepad mappings.
 * Reads HID input reports directly via IOKit on macOS, bypassing
 * GLFW/raylib's gamepad abstraction entirely.
 *
 * Usage (inside nix shell or with IOKit available):
 *   cc -o hid_dump sim/hid_dump.c -framework IOKit -framework CoreFoundation
 *   ./hid_dump
 *
 * Press buttons and move sticks on your Zorro. Watch which bytes change.
 * Then we build an SDL2 mapping string from the results.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <IOKit/hid/IOHIDManager.h>
#include <IOKit/hid/IOHIDDevice.h>
#include <CoreFoundation/CoreFoundation.h>

#define MAX_REPORT_SIZE 64
#define TARGET_VENDOR  4617   /* OpenTX */
#define TARGET_PRODUCT 20308  /* Radiomaster Zorro Joystick */

static uint8_t prev_report[MAX_REPORT_SIZE];
static int prev_len = 0;
static int first = 1;

static void report_callback(void *context, IOReturn result, void *sender,
                            IOHIDReportType type, uint32_t reportID,
                            uint8_t *report, CFIndex reportLength) {
    (void)context; (void)result; (void)sender; (void)type; (void)reportID;

    if (reportLength > MAX_REPORT_SIZE) reportLength = MAX_REPORT_SIZE;

    /* On first report, just store baseline. */
    if (first) {
        memcpy(prev_report, report, reportLength);
        prev_len = (int)reportLength;
        first = 0;
        printf("Got first report (%d bytes). Move sticks / press buttons:\n\n", prev_len);

        printf("Baseline: ");
        for (int i = 0; i < prev_len; i++) printf("%02x ", prev_report[i]);
        printf("\n\n");
        return;
    }

    /* Find changed bytes (ignore single-bit jitter). */
    int changed = 0;
    char changes[512] = {0};
    int clen = 0;
    for (int i = 0; i < reportLength && i < prev_len; i++) {
        int delta = (int)report[i] - (int)prev_report[i];
        if (delta < -1 || delta > 1) {  /* skip ±1 jitter */
            snprintf(changes + clen, sizeof(changes) - clen,
                     "  byte[%2d]: %3d -> %3d  (delta %+d)\n",
                     i, prev_report[i], report[i], delta);
            clen = (int)strlen(changes);
            changed++;
        }
    }

    if (changed > 0) {
        printf("--- %d byte(s) changed ---\n%s\n", changed, changes);
    }

    memcpy(prev_report, report, reportLength);
    prev_len = (int)reportLength;
}

int main(void) {
    IOHIDManagerRef mgr = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    if (!mgr) { fprintf(stderr, "Failed to create HID manager\n"); return 1; }

    /* Match only the Zorro. */
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
        fprintf(stderr, "Failed to open HID manager (0x%x). Is the Zorro plugged in?\n", ret);
        return 1;
    }

    /* Get matching device and register input report callback. */
    CFSetRef devices = IOHIDManagerCopyDevices(mgr);
    if (!devices || CFSetGetCount(devices) == 0) {
        fprintf(stderr, "No Zorro found. Check USB connection.\n");
        return 1;
    }

    /* Extract first (and only) device from the set. */
    const void *dev_ptr = NULL;
    CFSetGetValues(devices, &dev_ptr);
    IOHIDDeviceRef dev = (IOHIDDeviceRef)dev_ptr;
    printf("Found: Radiomaster Zorro Joystick (VID=%d PID=%d)\n", TARGET_VENDOR, TARGET_PRODUCT);

    static uint8_t report_buf[MAX_REPORT_SIZE];
    IOHIDDeviceRegisterInputReportCallback(dev, report_buf, MAX_REPORT_SIZE,
                                           report_callback, NULL);

    /* Schedule on run loop and spin. */
    IOHIDManagerScheduleWithRunLoop(mgr, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);

    printf("Waiting for HID reports... (Ctrl+C to quit)\n\n");
    CFRunLoopRun();

    IOHIDManagerClose(mgr, kIOHIDOptionsTypeNone);
    CFRelease(mgr);
    return 0;
}
