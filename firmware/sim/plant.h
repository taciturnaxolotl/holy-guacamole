#pragma once

/*
 * Box2D plant model for the SITL meltybrain simulator.
 *
 * Models the robot as a rigid disc in a top-down (gravity-free) 2D
 * world. Two drive motors at +/-E apply tangential thrust: their sum
 * spins the body, their difference produces a body-frame net force that
 * (when modulated against heading by the drift controller) translates
 * the robot across the arena. Arena walls give impacts; Box2D damping
 * gives drag.
 *
 * Absolute constants (inertia, thrust, damping) are plausible guesses
 * until tuned against real telemetry; the plant validates behaviour and
 * control logic, not exact spin-up time.
 */

#include <stdint.h>
#include "math/linalg.h"
#include "imu_synth.h"

typedef struct plant plant_t;

/* Create/destroy the plant. seed drives the IMU noise PRNG. */
plant_t *plant_create(uint64_t seed);
void     plant_destroy(plant_t *p);

/* Reset the robot to arena centre, at rest. */
void plant_reset(plant_t *p);

/* Advance the physics by dt seconds under the two motor throttles
 * (each [0,1]). */
void plant_step(plant_t *p, float throttle_a, float throttle_b, float dt);

/* Fill the SI measurement vector the IMU array would report right now
 * (from true angular velocity/acceleration, with noise + saturation). */
void plant_read_imu(plant_t *p, mat_t *z);

/* True-state accessors for visualization and scoring. */
float plant_true_heading(const plant_t *p);   /* rad, wrapped */
float plant_true_omega(const plant_t *p);     /* rad/s */
void  plant_position(const plant_t *p, float *x, float *y);  /* metres */
float plant_arena_size(const plant_t *p);     /* arena half-extent, metres */
