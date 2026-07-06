#pragma once

/*
 * Translational drift control for the meltybrain.
 *
 * The two drive motors are modulated sinusoidally against the estimated
 * heading so that net thrust points in a commanded world-frame
 * direction (see braindump section 11.5):
 *
 *   throttle_A(theta) = base + A * cos(theta - phi)
 *   throttle_B(theta) = base - A * cos(theta - phi)
 *
 *   base  - symmetric throttle setting the spin RPM
 *   A     - drift authority (0 = pure spin, higher = stronger translation)
 *   phi   - desired world-frame translation direction (rad)
 *   theta - current estimated heading (rad)
 *
 * Pure functions: no hardware, no state. The sign/phase convention that
 * maps a given phi to the physical translation direction is confirmed
 * on the bench; these functions provide the modulation shape and safe
 * clamping, which is what can be verified without the robot.
 */

typedef struct {
    float a;  /* motor A throttle, [0, 1] */
    float b;  /* motor B throttle, [0, 1] */
} drift_throttles_t;

/* Per-motor throttle for the current heading. Results clamped to [0, 1]. */
drift_throttles_t drift_compute(float theta, float base, float authority,
                                float phi);

/* Map an RC stick vector to drift authority and world-frame direction.
 * stick_x/stick_y are in [-1, 1]. Stick magnitude is clamped to 1 and
 * scaled by max_authority. Near-zero stick yields zero authority. */
void drift_from_stick(float stick_x, float stick_y, float max_authority,
                      float *authority, float *phi);
