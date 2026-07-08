#include "drift.h"

#include <math.h>

static float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

/* Wrap angle difference into [-pi, pi]. */
static float wrap_diff(float a) {
    while (a > (float)M_PI)  a -= 2.0f * (float)M_PI;
    while (a < -(float)M_PI) a += 2.0f * (float)M_PI;
    return a;
}

static drift_throttles_t drift_sinusoidal(float theta, float base,
                                          float authority, float phi) {
    /* Net translational force points at heading ± 90 deg. Adding pi/2
     * to phi compensates so commanded direction phi translates toward phi. */
    float mod = authority * cosf(theta - phi - (float)M_PI / 2.0f);
    drift_throttles_t out;
    out.a = clamp01(base + mod);
    out.b = clamp01(base - mod);
    return out;
}

static drift_throttles_t drift_square(float theta, float base,
                                      float authority, float phi) {
    /* Square wave modulation from arithebiker's AM32 approach:
     * Motor A gets base+authority when heading is within 90 deg of phi,
     * motor B gets base+authority for the other half. The +pi/2 offset
     * aligns the tangent force with the commanded direction (same as
     * sinusoidal). Braking window at transitions is handled by AM32's
     * internal ramping; we just switch which motor is boosted. */
    float diff = wrap_diff(theta - phi - (float)M_PI / 2.0f);
    drift_throttles_t out;
    if (diff >= 0.0f) {
        /* Heading in the "A boost" half */
        out.a = clamp01(base + authority);
        out.b = clamp01(base - authority * 0.15f);  /* slight brake on opposite */
    } else {
        /* Heading in the "B boost" half */
        out.a = clamp01(base - authority * 0.15f);
        out.b = clamp01(base + authority);
    }
    return out;
}

drift_throttles_t drift_compute(float theta, float base, float authority,
                                float phi, drift_mod_t mode) {
    if (mode == DRIFT_MOD_SQUARE)
        return drift_square(theta, base, authority, phi);
    return drift_sinusoidal(theta, base, authority, phi);
}

void drift_from_stick(float stick_x, float stick_y, float max_authority,
                      float *authority, float *phi) {
    float mag = sqrtf(stick_x * stick_x + stick_y * stick_y);

    if (mag < 1e-3f) {
        *authority = 0.0f;
        *phi = 0.0f;
        return;
    }

    if (mag > 1.0f) mag = 1.0f;
    *authority = mag * max_authority;
    *phi = atan2f(stick_y, stick_x);
}
