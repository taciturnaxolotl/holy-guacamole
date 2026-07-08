#include "accel_cal.h"

static float cal_table[ACCEL_CAL_MAX_POINTS * 2]; /* pairs: [raw_g, factor] */
static int cal_count = 0;

void accel_cal_init(void) {
    cal_count = 0;
}

bool accel_cal_add(float raw_g, float correction_factor) {
    if (cal_count >= ACCEL_CAL_MAX_POINTS) return false;

    /* Sorted insert by raw_g. */
    int pos = cal_count;
    while (pos > 0 && raw_g < cal_table[(pos - 1) * 2]) {
        cal_table[pos * 2]     = cal_table[(pos - 1) * 2];
        cal_table[pos * 2 + 1] = cal_table[(pos - 1) * 2 + 1];
        pos--;
    }
    cal_table[pos * 2]     = raw_g;
    cal_table[pos * 2 + 1] = correction_factor;
    cal_count++;
    return true;
}

float accel_cal_get(float raw_g) {
    if (cal_count == 0) return 1.0f;

    /* Below table range: use first point's factor. */
    if (raw_g <= cal_table[0]) return cal_table[1];

    /* Above table range: use last point's factor. */
    if (raw_g >= cal_table[(cal_count - 1) * 2])
        return cal_table[(cal_count - 1) * 2 + 1];

    /* Find bracketing interval and lerp. */
    for (int i = 1; i < cal_count; i++) {
        float g0 = cal_table[(i - 1) * 2];
        float g1 = cal_table[i * 2];
        if (raw_g <= g1) {
            float t = (raw_g - g0) / (g1 - g0);
            float f0 = cal_table[(i - 1) * 2 + 1];
            float f1 = cal_table[i * 2 + 1];
            return f0 + t * (f1 - f0);
        }
    }
    return 1.0f;  /* shouldn't reach here */
}

int accel_cal_count(void) {
    return cal_count;
}

void accel_cal_clear(void) {
    cal_count = 0;
}
