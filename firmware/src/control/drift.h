#pragma once

/*
 * Translational drift control for the meltybrain.
 *
 * Two modulation modes are available:
 *
 * SINUSOIDAL (default):
 *   throttle_A(theta) = base + A * cos(theta - phi - pi/2)
 *   throttle_B(theta) = base - A * cos(theta - phi - pi/2)
 *   Smooth modulation, less RPM ripple. Community-standard approach.
 *
 * SQUARE:
 *   Motor A gets base+authority for half a revolution centered on phi,
 *   motor B gets base+authority for the other half. Short braking window
 *   at transitions. From arithebiker's proven approach with AM32: better
 *   translation authority at high throttle, AM32's internal ramping
 *   smooths the edges.
 *
 * In both modes:
 *   base      - symmetric throttle setting the spin RPM
 *   authority - drift strength [0, max_authority]
 *   phi       - desired world-frame translation direction (rad)
 *   theta     - current estimated heading (rad)
 *
 * Pure functions: no hardware, no state.
 */

typedef enum {
    DRIFT_MOD_SINUSOIDAL = 0,
    DRIFT_MOD_SQUARE     = 1,
} drift_mod_t;

typedef struct {
    float a;  /* motor A throttle, [0, 1] */
    float b;  /* motor B throttle, [0, 1] */
} drift_throttles_t;

/* Per-motor throttle for the current heading. Results clamped to [0, 1]. */
drift_throttles_t drift_compute(float theta, float base, float authority,
                                float phi, drift_mod_t mode);

/* Map an RC stick vector to drift authority and world-frame direction.
 * stick_x/stick_y are in [-1, 1]. Stick magnitude is clamped to 1 and
 * scaled by max_authority. Near-zero stick yields zero authority. */
void drift_from_stick(float stick_x, float stick_y, float max_authority,
                      float *authority, float *phi);
