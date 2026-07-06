#pragma once

/*
 * Fixed-capacity float32 matrix math for the heading EKF.
 * No dynamic allocation: every matrix carries a MAX_DIM x MAX_DIM
 * backing store and tracks its logical rows/cols. This keeps the
 * code allocation-free (safe on the RP2350) and host-testable.
 *
 * float32 is deliberate: the RP2350 Cortex-M33 FPU is single-precision.
 * Host tests use the same type so numerical issues surface off-target.
 */

#include <stdint.h>
#include <stdbool.h>

/* Largest state/measurement dimension we support.
 * Reduced EKF uses 3 states; full EKF grows to 7. Measurement
 * vector is up to 7 (3 radial + 3 tangential + 1 gyro). */
#define MAT_MAX_DIM 8

typedef struct {
    int rows;
    int cols;
    float m[MAT_MAX_DIM * MAT_MAX_DIM];
} mat_t;

/* Element access (row-major). */
static inline float mat_get(const mat_t *a, int r, int c) {
    return a->m[r * a->cols + c];
}
static inline void mat_set(mat_t *a, int r, int c, float v) {
    a->m[r * a->cols + c] = v;
}

/* Initialize to given shape, all zeros. */
void mat_zero(mat_t *a, int rows, int cols);

/* Square identity of size n. */
void mat_identity(mat_t *a, int n);

/* dst = a + b. Shapes must match. */
void mat_add(mat_t *dst, const mat_t *a, const mat_t *b);

/* dst = a - b. Shapes must match. */
void mat_sub(mat_t *dst, const mat_t *a, const mat_t *b);

/* dst = a * b. Inner dims must match. dst must not alias a or b. */
void mat_mul(mat_t *dst, const mat_t *a, const mat_t *b);

/* dst = a^T. dst must not alias a. */
void mat_transpose(mat_t *dst, const mat_t *a);

/* dst = a * b^T. Convenience for covariance forms. */
void mat_mul_transpose(mat_t *dst, const mat_t *a, const mat_t *b);

/* Invert square matrix a into dst via Gauss-Jordan with partial
 * pivoting. Returns false if singular. dst must not alias a. */
bool mat_invert(mat_t *dst, const mat_t *a);

/* Force symmetry: a = (a + a^T) / 2. Guards covariance against
 * float32 rounding drift. Square only. */
void mat_symmetrize(mat_t *a);

/* True if any element is NaN or Inf. */
bool mat_is_finite(const mat_t *a);
