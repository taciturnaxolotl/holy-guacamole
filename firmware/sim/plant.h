#pragma once

/*
 * Hand-rolled 2D rigid-disc plant for the SITL meltybrain simulator.
 *
 * Models the robot as a rigid disc in a top-down (gravity-free) plane.
 * State is {x, y, vx, vy, theta, omega}; heading theta is integrated as
 * the trapezoidal integral of omega (matching the EKF's midpoint predict)
 * rather than a separate orientation, because at meltybrain RPM a naive
 * per-step rotation aliases badly.
 *
 * Two drive motors sit at +/-r_w on the body x-axis and push tangentially
 * (body -/+ y). Their sum spins the body; their difference is a body-frame
 * net force that, modulated against heading by the drift controller,
 * translates the robot. A back-EMF torque-speed curve sets terminal RPM;
 * a first-order ESC lag shapes spin-up; Coulomb floor friction opposes
 * translation. Arena walls give an explicit friction-cone contact impulse
 * (normal bounce + tangential skitter + spin bleed).
 *
 * There is no external physics engine: circle-vs-square collision is
 * analytic, so the plant is fully deterministic. All constants live in
 * plant_params_t so tuning is one place and scenarios can sweep them.
 * Defaults are anchored to the real robot (see docs/firmware.md); absolute
 * values are plausible until tuned against telemetry.
 */

#include <stdint.h>
#include "math/linalg.h"
#include "imu_synth.h"

typedef struct plant plant_t;

/* Tunable plant configuration. See plant_params_default for anchored
 * defaults and docs/firmware.md for the reasoning behind each value. */
typedef struct {
    /* Body */
    float mass_kg;         /* chassis mass */
    float body_radius_m;   /* disc body radius (mass distribution) */
    float tip_radius_m;    /* weapon-tip envelope = wall collision radius */
    float inertia_factor;  /* k in I = k*m*body_radius^2 */

    /* Drivetrain */
    float motor_offset_m;  /* r_w: drive-wheel lever from centre */
    float omega_free;      /* terminal omega at full throttle (rad/s) */
    float spin_tau_s;      /* spin-up time constant (s) */
    float esc_tau_s;       /* first-order ESC throttle lag (s) */

    /* Floor / arena */
    float floor_mu;        /* Coulomb translation friction coefficient */
    float floor_viscous;   /* small linear translation damping (N*s/m per kg) */
    float arena_half_m;    /* arena half-extent (square) */
    float wall_restitution;/* normal bounce coefficient e */
    float wall_mu;         /* rim-wall friction coefficient (skitter/bleed) */
} plant_params_t;

/* Fill p with anchored defaults for the real robot. */
void plant_params_default(plant_params_t *p);

/* Create with default params / with explicit params. seed drives the IMU
 * noise PRNG. */
plant_t *plant_create(uint64_t seed);
plant_t *plant_create_params(uint64_t seed, const plant_params_t *params);
void     plant_destroy(plant_t *p);

/* Reset the robot to arena centre, at rest (params unchanged). */
void plant_reset(plant_t *p);

/* Advance the physics by dt seconds under the two motor throttles
 * (each [0,1]). */
void plant_step(plant_t *p, float throttle_a, float throttle_b, float dt);

/* Instantaneously add domega to the spin (impact model, for scenarios). */
void plant_kick_omega(plant_t *p, float domega);

/* Directly set position and velocity (scenario setup, e.g. to place the
 * disc near a wall moving into it for a deterministic contact test). */
void plant_set_pose(plant_t *p, float x, float y, float vx, float vy);

/* Access the synthetic-IMU model to toggle error sources per scenario
 * (e.g. disable nonlinearity to represent an accel_cal-calibrated sensor). */
imu_synth_t *plant_synth(plant_t *p);

/* Fill the SI measurement vector the IMU array would report right now
 * (from true angular velocity/acceleration, with noise + saturation).
 * dt is the tick period (drives gyro bias walk + vibration phase). */
void plant_read_imu(plant_t *p, mat_t *z, float dt);

/* True-state accessors for visualization and scoring. */
float plant_true_heading(const plant_t *p);   /* rad, wrapped [0,2pi) */
float plant_true_omega(const plant_t *p);     /* rad/s */
float plant_true_alpha(const plant_t *p);     /* rad/s^2 */
void  plant_position(const plant_t *p, float *x, float *y);  /* metres */
float plant_arena_size(const plant_t *p);     /* arena half-extent, metres */
float plant_body_radius(const plant_t *p);    /* disc body radius, metres */
float plant_tip_radius(const plant_t *p);     /* weapon-tip collision radius, m */
