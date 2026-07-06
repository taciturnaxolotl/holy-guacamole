#include "drift.h"

#include <math.h>

static float clamp01(float v) {
    if (v < 0.0f) return 0.0f;
    if (v > 1.0f) return 1.0f;
    return v;
}

drift_throttles_t drift_compute(float theta, float base, float authority,
                                float phi) {
    float mod = authority * cosf(theta - phi);
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
