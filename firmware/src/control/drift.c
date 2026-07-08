#include "drift.h"

#include <math.h>

static float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

drift_throttles_t drift_compute(float theta, float base, float authority,
                                float phi) {
    /* Net translational force from the tangential motor pair points at
     * heading ± 90 deg (the tangent direction). The cosine modulation
     * peaks the differential when theta ≈ phi, but that makes the force
     * point at phi - 90 deg. Adding pi/2 to phi compensates so that a
     * commanded world direction phi actually translates toward phi. */
    float mod = authority * cosf(theta - phi - (float)M_PI / 2.0f);
    drift_throttles_t out;
    out.a = clamp01(base + mod);
    out.b = clamp01(base - mod);
    return out;
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
