#pragma once

/*
 * Heading estimator output, shared across all sensor sources and consumers.
 */

typedef struct {
    float heading;   /* wrapped heading, rad [0, 2π) */
    float omega;     /* angular velocity, rad/s */
    float alpha;     /* angular acceleration, rad/s^2 */
} heading_estimate_t;
