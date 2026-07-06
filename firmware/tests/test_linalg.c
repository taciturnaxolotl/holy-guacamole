#include "test_assert.h"
#include "math/linalg.h"

static void test_identity_mul(void) {
    mat_t id, a, out;
    mat_identity(&id, 3);
    mat_zero(&a, 3, 3);
    mat_set(&a, 0, 0, 1.0f); mat_set(&a, 0, 1, 2.0f); mat_set(&a, 0, 2, 3.0f);
    mat_set(&a, 1, 0, 4.0f); mat_set(&a, 1, 1, 5.0f); mat_set(&a, 1, 2, 6.0f);
    mat_set(&a, 2, 0, 7.0f); mat_set(&a, 2, 1, 8.0f); mat_set(&a, 2, 2, 10.0f);

    mat_mul(&out, &id, &a);
    for (int i = 0; i < 9; i++) ASSERT_NEAR(out.m[i], a.m[i], 1e-6f);
}

static void test_mul_known(void) {
    /* [1 2; 3 4] * [5 6; 7 8] = [19 22; 43 50] */
    mat_t a, b, out;
    mat_zero(&a, 2, 2);
    mat_set(&a, 0, 0, 1); mat_set(&a, 0, 1, 2);
    mat_set(&a, 1, 0, 3); mat_set(&a, 1, 1, 4);
    mat_zero(&b, 2, 2);
    mat_set(&b, 0, 0, 5); mat_set(&b, 0, 1, 6);
    mat_set(&b, 1, 0, 7); mat_set(&b, 1, 1, 8);

    mat_mul(&out, &a, &b);
    ASSERT_NEAR(mat_get(&out, 0, 0), 19.0f, 1e-5f);
    ASSERT_NEAR(mat_get(&out, 0, 1), 22.0f, 1e-5f);
    ASSERT_NEAR(mat_get(&out, 1, 0), 43.0f, 1e-5f);
    ASSERT_NEAR(mat_get(&out, 1, 1), 50.0f, 1e-5f);
}

static void test_transpose(void) {
    mat_t a, t;
    mat_zero(&a, 2, 3);
    mat_set(&a, 0, 0, 1); mat_set(&a, 0, 1, 2); mat_set(&a, 0, 2, 3);
    mat_set(&a, 1, 0, 4); mat_set(&a, 1, 1, 5); mat_set(&a, 1, 2, 6);

    mat_transpose(&t, &a);
    ASSERT_TRUE(t.rows == 3 && t.cols == 2);
    ASSERT_NEAR(mat_get(&t, 0, 0), 1.0f, 1e-6f);
    ASSERT_NEAR(mat_get(&t, 2, 1), 6.0f, 1e-6f);
    ASSERT_NEAR(mat_get(&t, 1, 0), 2.0f, 1e-6f);
}

static void test_invert_identity(void) {
    mat_t id, inv;
    mat_identity(&id, 4);
    ASSERT_TRUE(mat_invert(&inv, &id));
    for (int i = 0; i < 16; i++) ASSERT_NEAR(inv.m[i], id.m[i], 1e-6f);
}

static void test_invert_known(void) {
    /* A * A^-1 should be I. Use a well-conditioned 3x3. */
    mat_t a, inv, prod;
    mat_zero(&a, 3, 3);
    mat_set(&a, 0, 0, 4); mat_set(&a, 0, 1, 3); mat_set(&a, 0, 2, 0);
    mat_set(&a, 1, 0, 3); mat_set(&a, 1, 1, 4); mat_set(&a, 1, 2, 0);
    mat_set(&a, 2, 0, 0); mat_set(&a, 2, 1, 0); mat_set(&a, 2, 2, 2);

    ASSERT_TRUE(mat_invert(&inv, &a));
    mat_mul(&prod, &a, &inv);
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 3; c++)
            ASSERT_NEAR(mat_get(&prod, r, c), r == c ? 1.0f : 0.0f, 1e-5f);
}

static void test_invert_singular(void) {
    mat_t a, inv;
    mat_zero(&a, 2, 2);  /* all zeros -> singular */
    ASSERT_TRUE(!mat_invert(&inv, &a));
}

static void test_symmetrize(void) {
    mat_t a;
    mat_zero(&a, 2, 2);
    mat_set(&a, 0, 0, 1); mat_set(&a, 0, 1, 2);
    mat_set(&a, 1, 0, 4); mat_set(&a, 1, 1, 3);
    mat_symmetrize(&a);
    ASSERT_NEAR(mat_get(&a, 0, 1), 3.0f, 1e-6f);  /* (2+4)/2 */
    ASSERT_NEAR(mat_get(&a, 1, 0), 3.0f, 1e-6f);
}

int main(void) {
    RUN_TEST(test_identity_mul);
    RUN_TEST(test_mul_known);
    RUN_TEST(test_transpose);
    RUN_TEST(test_invert_identity);
    RUN_TEST(test_invert_known);
    RUN_TEST(test_invert_singular);
    RUN_TEST(test_symmetrize);
    return test_report();
}
