#include "linalg.h"

#include <math.h>

void mat_zero(mat_t *a, int rows, int cols) {
    a->rows = rows;
    a->cols = cols;
    for (int i = 0; i < rows * cols; i++) a->m[i] = 0.0f;
}

void mat_identity(mat_t *a, int n) {
    mat_zero(a, n, n);
    for (int i = 0; i < n; i++) a->m[i * n + i] = 1.0f;
}

void mat_add(mat_t *dst, const mat_t *a, const mat_t *b) {
    dst->rows = a->rows;
    dst->cols = a->cols;
    for (int i = 0; i < a->rows * a->cols; i++) dst->m[i] = a->m[i] + b->m[i];
}

void mat_sub(mat_t *dst, const mat_t *a, const mat_t *b) {
    dst->rows = a->rows;
    dst->cols = a->cols;
    for (int i = 0; i < a->rows * a->cols; i++) dst->m[i] = a->m[i] - b->m[i];
}

void mat_mul(mat_t *dst, const mat_t *a, const mat_t *b) {
    dst->rows = a->rows;
    dst->cols = b->cols;
    for (int r = 0; r < a->rows; r++) {
        for (int c = 0; c < b->cols; c++) {
            float sum = 0.0f;
            for (int k = 0; k < a->cols; k++) {
                sum += a->m[r * a->cols + k] * b->m[k * b->cols + c];
            }
            dst->m[r * dst->cols + c] = sum;
        }
    }
}

void mat_transpose(mat_t *dst, const mat_t *a) {
    dst->rows = a->cols;
    dst->cols = a->rows;
    for (int r = 0; r < a->rows; r++) {
        for (int c = 0; c < a->cols; c++) {
            dst->m[c * dst->cols + r] = a->m[r * a->cols + c];
        }
    }
}

void mat_mul_transpose(mat_t *dst, const mat_t *a, const mat_t *b) {
    /* dst = a * b^T : (a.rows x a.cols) * (b.cols x b.rows) */
    dst->rows = a->rows;
    dst->cols = b->rows;
    for (int r = 0; r < a->rows; r++) {
        for (int c = 0; c < b->rows; c++) {
            float sum = 0.0f;
            for (int k = 0; k < a->cols; k++) {
                sum += a->m[r * a->cols + k] * b->m[c * b->cols + k];
            }
            dst->m[r * dst->cols + c] = sum;
        }
    }
}

bool mat_invert(mat_t *dst, const mat_t *a) {
    int n = a->rows;
    if (n != a->cols) return false;

    /* Work on an augmented copy [a | I]; reduce a to I, dst becomes inverse. */
    float work[MAT_MAX_DIM * MAT_MAX_DIM];
    for (int i = 0; i < n * n; i++) work[i] = a->m[i];
    mat_identity(dst, n);

    for (int col = 0; col < n; col++) {
        /* Partial pivot: find largest magnitude in this column at/below diagonal. */
        int pivot = col;
        float best = fabsf(work[col * n + col]);
        for (int r = col + 1; r < n; r++) {
            float v = fabsf(work[r * n + col]);
            if (v > best) {
                best = v;
                pivot = r;
            }
        }
        if (best < 1e-20f) return false;  /* singular */

        /* Swap pivot row into place in both work and dst. */
        if (pivot != col) {
            for (int c = 0; c < n; c++) {
                float t = work[col * n + c];
                work[col * n + c] = work[pivot * n + c];
                work[pivot * n + c] = t;
                t = dst->m[col * n + c];
                dst->m[col * n + c] = dst->m[pivot * n + c];
                dst->m[pivot * n + c] = t;
            }
        }

        /* Normalize pivot row. */
        float pv = work[col * n + col];
        for (int c = 0; c < n; c++) {
            work[col * n + c] /= pv;
            dst->m[col * n + c] /= pv;
        }

        /* Eliminate this column from all other rows. */
        for (int r = 0; r < n; r++) {
            if (r == col) continue;
            float factor = work[r * n + col];
            if (factor == 0.0f) continue;
            for (int c = 0; c < n; c++) {
                work[r * n + c] -= factor * work[col * n + c];
                dst->m[r * n + c] -= factor * dst->m[col * n + c];
            }
        }
    }
    return true;
}

void mat_symmetrize(mat_t *a) {
    int n = a->rows;
    for (int r = 0; r < n; r++) {
        for (int c = r + 1; c < n; c++) {
            float avg = 0.5f * (a->m[r * n + c] + a->m[c * n + r]);
            a->m[r * n + c] = avg;
            a->m[c * n + r] = avg;
        }
    }
}

bool mat_is_finite(const mat_t *a) {
    for (int i = 0; i < a->rows * a->cols; i++) {
        if (!isfinite(a->m[i])) return false;
    }
    return true;
}
