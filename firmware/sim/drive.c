/*
 * Interactive SITL test-drive harness.
 *
 * Runs the EXACT estimation + control code (app_sensor_tick_si +
 * app_control_tick) against the Box2D plant, closing the loop, and
 * renders a top-down view so you can drive the robot and watch how the
 * EKF heading estimate tracks (or lags) the true heading.
 *
 * Controls:
 *   W / S        spin up / down (base throttle)
 *   Arrow keys   drift direction (world frame)
 *   SPACE        toggle closed-loop drift vs open-loop spin
 *   T            trim heading (align "forward" to current true heading)
 *   R            reset
 *   ESC          quit
 */

#include <math.h>
#include <stdio.h>

#include "raylib.h"

#include "math/linalg.h"
#include "estimation/ekf.h"
#include "estimation/meas_model.h"
#include "estimation/imu_geom.h"
#include "app/control_loop.h"
#include "plant.h"

#define SCREEN   820
#define TICK_DT  0.001f          /* 1 kHz control/physics tick */
#define TWO_PI   6.28318530718f

/* World metres -> screen pixels (y flipped: world up = screen up). */
static Vector2 world_to_screen(float x, float y, float px_per_m) {
    return (Vector2){ SCREEN * 0.5f + x * px_per_m,
                      SCREEN * 0.5f - y * px_per_m };
}

int main(void) {
    InitWindow(SCREEN, SCREEN, "Holy Guacamole - SITL");
    SetTargetFPS(60);

    plant_t *plant = plant_create(0xBEEF);
    /* Calibrated sensor: the real robot removes the H3LIS nonlinearity with
     * accel_cal, which this SI path doesn't run. Left on it walks heading. */
    plant_synth(plant)->enable_nonlinearity = false;
    ekf_t ekf;
    ekf_init(&ekf, 0.0f);
    app_config_t cfg;
    app_config_default(&cfg);
    printf("drift_phase=%.3f rad (%.1f deg) — if this says -1.571 the binary is stale\n",
           (double)cfg.drift_phase, (double)(cfg.drift_phase * 57.2958));

    float base = 0.0f;
    double accumulator = 0.0;
    app_estimate_t est = {0};
    app_motors_t motors = {0};

    /* Heading-strobe state: emulates the real robot's heading LED, which
     * flashes once per revolution when the ESTIMATED heading passes a
     * fixed reference. We latch the TRUE physical heading at each flash.
     * If the estimate is locked, that latched angle sits still; if it
     * drifts, the strobe walks around the rim. */
    float prev_trimmed = 0.0f;
    float strobe_true = 0.0f;   /* true heading at last strobe flash */
    float strobe_flash = 0.0f;  /* brightness envelope [0,1] */

    while (!WindowShouldClose()) {
        /* ---- input ---- */
        if (IsKeyDown(KEY_W)) base += 0.4f * GetFrameTime();
        if (IsKeyDown(KEY_S)) base -= 0.4f * GetFrameTime();
        if (base < 0.0f) base = 0.0f;
        if (base > 1.0f) base = 1.0f;
        /* A/D nudge the heading trim so you can rotate "forward" to taste. */
        if (IsKeyDown(KEY_A)) cfg.heading_trim += 1.5f * GetFrameTime();
        if (IsKeyDown(KEY_D)) cfg.heading_trim -= 1.5f * GetFrameTime();
        if (IsKeyPressed(KEY_SPACE)) cfg.drift_enabled = !cfg.drift_enabled;
        if (IsKeyPressed(KEY_T)) {
            /* Align "forward": trim so control heading matches true heading.
             * On the real robot the operator does this by eye against the
             * heading LED; here we use the sim's ground truth as the eye. */
            float e = est.heading - plant_true_heading(plant);
            cfg.heading_trim = e;
        }
        if (IsKeyPressed(KEY_R)) { plant_reset(plant); ekf_init(&ekf, 0.0f); base = 0.0f; cfg.heading_trim = 0.0f; }

        app_command_t cmd = {0};
        cmd.armed = true;
        cmd.base = base;
        cmd.stick_x = (float)(IsKeyDown(KEY_RIGHT) - IsKeyDown(KEY_LEFT));
        cmd.stick_y = (float)(IsKeyDown(KEY_UP) - IsKeyDown(KEY_DOWN));

        /* ---- fixed-step physics + the real control code ---- */
        accumulator += GetFrameTime();
        int guard = 0;
        mat_t last_z;
        mat_zero(&last_z, MEAS_DIM, 1);
        while (accumulator >= TICK_DT && guard++ < 100) {
            mat_t z;
            plant_read_imu(plant, &z, TICK_DT);
            last_z = z;
            est = app_sensor_tick_si(&ekf, &z, TICK_DT);
            motors = app_control_tick(&cfg, &cmd, &est, TICK_DT);
            plant_step(plant, motors.throttle_a, motors.throttle_b, TICK_DT);
            accumulator -= TICK_DT;

            /* Strobe: fire when the trimmed estimated heading wraps past
             * the reference (once per revolution). Latch true heading. */
            float trimmed = est.heading - cfg.heading_trim;
            trimmed = wrap_0_2pi(trimmed);
            if (prev_trimmed - trimmed > (float)M_PI) {
                strobe_true = plant_true_heading(plant);
                strobe_flash = 1.0f;
            }
            prev_trimmed = trimmed;
        }

        /* ---- render ---- */
        float arena = plant_arena_size(plant);
        float px_per_m = (SCREEN * 0.45f) / arena;
        float rx, ry;
        plant_position(plant, &rx, &ry);
        float true_hdg = plant_true_heading(plant);
        float body_m = plant_body_radius(plant);
        float tip_m = plant_tip_radius(plant);
        float body_px = body_m * px_per_m;
        float tip_px = tip_m * px_per_m;

        BeginDrawing();
        ClearBackground((Color){18, 18, 24, 255});

        /* arena bounds */
        Vector2 tl = world_to_screen(-arena, arena, px_per_m);
        DrawRectangleLines((int)tl.x, (int)tl.y, (int)(2 * arena * px_per_m),
                           (int)(2 * arena * px_per_m), (Color){80, 80, 100, 255});

        Vector2 c = world_to_screen(rx, ry, px_per_m);
        /* Weapon-tip envelope = the collision radius that touches the wall. */
        DrawCircleLinesV(c, tip_px, (Color){110, 90, 70, 255});
        /* Body disc (carries the mass). */
        DrawCircleV(c, body_px, (Color){60, 140, 90, 255});

        /* Per-IMU saturation dots at each sensor's body position. Green =
         * live, red = railed (its radial accel is clipped and the filter
         * has dropped it). At high RPM the outer sensors rail first, then
         * the inner; watch them go red as you spin up. */
        bool sat[MEAS_DIM];
        meas_saturation_flags(&last_z, sat);
        int imu_radial[3] = { MEAS_A_RADIAL, MEAS_B_RADIAL, MEAS_C_RADIAL };
        for (int i = 0; i < 3; i++) {
            float ang = true_hdg + imu_geom[i].angle_rad;
            float r = (imu_geom[i].radius_m / body_m) * body_px;
            Vector2 ip = { c.x + cosf(ang) * r, c.y - sinf(ang) * r };
            Color col = sat[imu_radial[i]] ? (Color){240, 70, 70, 255}
                                           : (Color){90, 220, 120, 255};
            DrawCircleV(ip, 5.0f, col);
        }

        /* Thin faint spoke at the true instantaneous heading: shows the
         * disc is physically spinning (it aliases at RPM, expected). */
        Vector2 spoke = { c.x + cosf(true_hdg) * tip_px,
                          c.y - sinf(true_hdg) * tip_px };
        DrawLineEx(c, spoke, 1.5f, (Color){70, 90, 80, 255});

        /* Heading strobe (the "heading LED"): a beacon at the physical
         * angle where the estimate last crossed forward. Locked estimate
         * -> beacon sits still. Drifting estimate -> beacon walks. */
        strobe_flash *= 0.90f;  /* fade between flashes */
        float beam = tip_px + 18.0f;
        Vector2 sdot = { c.x + cosf(strobe_true) * beam,
                         c.y - sinf(strobe_true) * beam };
        unsigned char b = (unsigned char)(120 + 135 * strobe_flash);
        DrawCircleV(sdot, 7.0f, (Color){255, 170, 40, b});
        DrawLineEx(c, sdot, 2.0f, (Color){255, 170, 40, (unsigned char)(60 + 120 * strobe_flash)});

        /* throttle bars */
        DrawRectangle(20, SCREEN - 30, (int)(motors.throttle_a * 200), 12,
                      (Color){240, 120, 220, 255});
        DrawRectangle(20, SCREEN - 15, (int)(motors.throttle_b * 200), 12,
                      (Color){120, 200, 240, 255});

        float rpm = plant_true_omega(plant) * 60.0f / TWO_PI;
        /* Control error = truth vs the TRIMMED estimate the controller
         * actually steers by. This is what matters; the raw offset is a
         * fixed spinup bias that trim cancels. */
        float ctl_err = fabsf(fmodf(true_hdg - (est.heading - cfg.heading_trim)
                                    + 3.0f * TWO_PI, TWO_PI));
        if (ctl_err > TWO_PI - ctl_err) ctl_err = TWO_PI - ctl_err;
        DrawText(TextFormat("RPM %.0f   w %.0f rad/s", (double)rpm,
                            (double)plant_true_omega(plant)), 20, 20, 20, RAYWHITE);
        DrawText(TextFormat("base %.2f   drift %s", (double)base,
                            cfg.drift_enabled ? "ON" : "OFF"), 20, 46, 20,
                 cfg.drift_enabled ? (Color){120, 240, 140, 255} : GRAY);
        DrawText(TextFormat("lock err %.1f deg   trim %.0f deg  (T set, A/D nudge)",
                            (double)(ctl_err * 57.2958f),
                            (double)(cfg.heading_trim * 57.2958f)), 20, 72, 20,
                 ctl_err < 0.17f ? (Color){120, 240, 140, 255} : RAYWHITE);
        DrawText("W/S spin  A/D trim  arrows drift  SPACE mode  T lock  R reset",
                 20, SCREEN - 58, 16, (Color){140, 140, 160, 255});

        /* Translation direction arrow: shows where the robot actually moved
         * over the last frame, so you can verify stick -> movement mapping. */
        {
            float rx2, ry2;
            plant_position(plant, &rx2, &ry2);
            float tdx = rx2 - rx, tdy = ry2 - ry;
            float tmag = sqrtf(tdx * tdx + tdy * tdy);
            if (tmag > 1e-5f) {
                float tdir = atan2f(tdy, tdx);
                float arrlen = 40.0f;
                Vector2 aend = { c.x + cosf(tdir) * arrlen,
                                 c.y - sinf(tdir) * arrlen };
                DrawLineEx(c, aend, 3.0f, (Color){100, 200, 255, 200});
            }
        }

        EndDrawing();
    }

    plant_destroy(plant);
    CloseWindow();
    return 0;
}
