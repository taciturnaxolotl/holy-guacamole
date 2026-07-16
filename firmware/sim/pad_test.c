/*
 * Gamepad test harness for verifying Zorro (or any controller) bindings.
 * Shows raw axis values, button states, and raylib gamepad detection info.
 *
 * Build inside nix shell:
 *   cmake -B build-sim -S sim && cmake --build build-sim --target pad_test
 *   ./build-sim/pad_test
 */

#include <stdio.h>
#include <math.h>
#include "raylib.h"

#define SCREEN_W 900
#define SCREEN_H 600
#define MAX_PADS 4

static const char *axis_name(int axis) {
    switch (axis) {
        case GAMEPAD_AXIS_LEFT_X:        return "L-Stick X";
        case GAMEPAD_AXIS_LEFT_Y:        return "L-Stick Y";
        case GAMEPAD_AXIS_RIGHT_X:       return "R-Stick X";
        case GAMEPAD_AXIS_RIGHT_Y:       return "R-Stick Y";
        case GAMEPAD_AXIS_LEFT_TRIGGER:  return "L-Trigger";
        case GAMEPAD_AXIS_RIGHT_TRIGGER: return "R-Trigger";
        default:                         return "Unknown";
    }
}

static const char *btn_name(int btn) {
    switch (btn) {
        case GAMEPAD_BUTTON_LEFT_FACE_UP:     return "D-Up";
        case GAMEPAD_BUTTON_LEFT_FACE_RIGHT:  return "D-Right";
        case GAMEPAD_BUTTON_LEFT_FACE_DOWN:   return "D-Down";
        case GAMEPAD_BUTTON_LEFT_FACE_LEFT:   return "D-Left";
        case GAMEPAD_BUTTON_RIGHT_FACE_UP:    return "Y/Triangle";
        case GAMEPAD_BUTTON_RIGHT_FACE_RIGHT: return "B/Circle";
        case GAMEPAD_BUTTON_RIGHT_FACE_DOWN:  return "A/Cross";
        case GAMEPAD_BUTTON_RIGHT_FACE_LEFT:  return "X/Square";
        case GAMEPAD_BUTTON_LEFT_TRIGGER_1:   return "LB/L1";
        case GAMEPAD_BUTTON_LEFT_TRIGGER_2:   return "LT/L2";
        case GAMEPAD_BUTTON_RIGHT_TRIGGER_1:  return "RB/R1";
        case GAMEPAD_BUTTON_RIGHT_TRIGGER_2:  return "RT/R2";
        case GAMEPAD_BUTTON_MIDDLE_LEFT:      return "Select/Back";
        case GAMEPAD_BUTTON_MIDDLE:           return "Home/Guide";
        case GAMEPAD_BUTTON_MIDDLE_RIGHT:     return "Start";
        case GAMEPAD_BUTTON_LEFT_THUMB:       return "L-Stick Click";
        case GAMEPAD_BUTTON_RIGHT_THUMB:      return "R-Stick Click";
        default:                              return "Unknown";
    }
}

int main(void) {
    InitWindow(SCREEN_W, SCREEN_H, "Gamepad Test Harness");
    SetTargetFPS(60);

    printf("=== Gamepad Test Harness ===\n");
    printf("Plug in your controller and press buttons / move sticks.\n");
    printf("Press ESC to quit.\n\n");

    while (!WindowShouldClose()) {
        BeginDrawing();
        ClearBackground((Color){20, 20, 28, 255});

        int y = 10;
        DrawText("GAMEPAD TEST HARNESS", 20, y, 24, (Color){240, 170, 40, 255});
        y += 35;

        bool any_pad = false;
        for (int p = 0; p < MAX_PADS; p++) {
            if (!IsGamepadAvailable(p)) continue;
            any_pad = true;

            const char *name = GetGamepadName(p);
            DrawText(TextFormat("Gamepad %d: %s", p, name ? name : "(no name)"),
                     20, y, 18, (Color){120, 240, 140, 255});
            printf("\rGamepad %d detected: %s                    \n", p, name ? name : "(no name)");
            y += 24;

            /* Axes */
            DrawText("AXES:", 30, y, 14, (Color){180, 180, 200, 255});
            y += 18;
            for (int a = 0; a < 6; a++) {
                float val = GetGamepadAxisMovement(p, a);
                Color col = fabsf(val) > 0.1f ? (Color){240, 200, 80, 255}
                                              : (Color){120, 120, 140, 255};

                /* Bar visualization */
                int bar_x = 200;
                int bar_w = 200;
                int bar_cx = bar_x + bar_w / 2;
                DrawRectangle(bar_x, y, bar_w, 12, (Color){40, 40, 50, 255});
                DrawLine(bar_cx, y, bar_cx, y + 12, (Color){80, 80, 100, 255});
                int fill = (int)(val * bar_w / 2);
                if (fill > 0)
                    DrawRectangle(bar_cx, y, fill, 12, col);
                else
                    DrawRectangle(bar_cx + fill, y, -fill, 12, col);

                DrawText(TextFormat("%-12s %+.3f", axis_name(a), (double)val),
                         30, y, 13, col);

                /* Print to console when axis moves */
                if (fabsf(val) > 0.15f)
                    printf("  Axis %-12s = %+.3f\n", axis_name(a), (double)val);

                y += 16;
            }

            y += 6;

            /* Buttons */
            DrawText("BUTTONS:", 30, y, 14, (Color){180, 180, 200, 255});
            y += 18;
            int bx = 30;
            int col_count = 0;
            for (int b = 0; b < 18; b++) {
                bool down = IsGamepadButtonDown(p, b);
                Color col = down ? (Color){120, 240, 140, 255}
                                 : (Color){80, 80, 100, 255};

                /* Dot indicator */
                DrawCircle(bx + 6, y + 6, 5.0f, col);
                DrawText(TextFormat("%s", btn_name(b)), bx + 16, y, 11, col);

                if (down)
                    printf("  Button %-14s PRESSED\n", btn_name(b));

                bx += 160;
                col_count++;
                if (col_count >= 4) {
                    bx = 30;
                    y += 16;
                    col_count = 0;
                }
            }
            y += 30;
        }

        if (!any_pad) {
            DrawText("No gamepad detected.", 20, y + 20, 20, (Color){200, 80, 80, 255});
            DrawText("Check USB connection and try unplugging/replugging.",
                     20, y + 48, 14, (Color){140, 140, 160, 255});
            DrawText("On macOS: System Settings > Game Controllers to verify OS sees it.",
                     20, y + 68, 14, (Color){140, 140, 160, 255});
        }

        DrawText("ESC to quit", SCREEN_W - 100, SCREEN_H - 20, 12,
                 (Color){100, 100, 120, 255});

        EndDrawing();
    }

    CloseWindow();
    printf("\nDone.\n");
    return 0;
}
