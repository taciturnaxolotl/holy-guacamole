#include "autocorr.h"

/* Maximum lags we'll compute. Static buffer avoids blowing the
 * RP2350 4KB core stack when called from interrupt/receive context. */
#define MAX_LAGS 800
#define MIN_PEAK_HEIGHT 0.15f

static float s_acorr[MAX_LAGS];

autocorr_result_t autocorr_find_period(const float *buf, uint32_t n,
                                       uint32_t min_lag, uint32_t max_lag) {
    autocorr_result_t res = { .valid = false };

    if (n < max_lag * 2 || max_lag > MAX_LAGS) return res;
    if (min_lag >= max_lag) return res;

    /* Batch mean for DC removal. This is the single canonical DC
     * removal point; upstream interpolation does NOT remove DC. */
    float mean = 0;
    for (uint32_t i = 0; i < n; i++) mean += buf[i];
    mean /= (float)n;

    /* Lag 0 for normalization. */
    float norm = 0;
    for (uint32_t i = 0; i < n; i++) {
        float v = buf[i] - mean;
        norm += v * v;
    }
    norm /= (float)n;
    s_acorr[0] = 1.0f;

    if (norm < 1e-10f) return res;

    for (uint32_t lag = 1; lag < max_lag && lag < n; lag++) {
        float s = 0;
        uint32_t cnt = n - lag;
        for (uint32_t i = 0; i < cnt; i++)
            s += (buf[i] - mean) * (buf[i + lag] - mean);
        s_acorr[lag] = (s / (float)cnt) / norm;
    }

    /* Find first significant peak after min_lag. */
    uint32_t best_lag = 0;
    float best_val = 0;

    for (uint32_t lag = min_lag; lag < max_lag - 1 && lag < n / 2; lag++) {
        if (s_acorr[lag] > best_val &&
            s_acorr[lag] > s_acorr[lag - 1] &&
            s_acorr[lag] > s_acorr[lag + 1]) {
            best_val = s_acorr[lag];
            best_lag = lag;
        }
    }

    if (best_lag > 0 && best_val >= MIN_PEAK_HEIGHT) {
        res.period_samples = best_lag;
        res.confidence = best_val;
        res.valid = true;
    }

    return res;
}
