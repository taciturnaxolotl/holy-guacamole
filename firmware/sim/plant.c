#include "plant.h"
#include "imu_synth.h"
#include "estimation/imu_geom.h"

#include <stdlib.h>
#include <math.h>

#define TWO_PI 6.28318530718f
#define GRAVITY 9.80665f

struct plant {
    plant_params_t prm;

    /* Derived motor constants (from prm; see recompute_motor). */
    float inertia;      /* I = k*m*body_radius^2 */
    float motor_fs;     /* per-motor stall force at full throttle (N) */
    float motor_kb;     /* back-EMF force coefficient (N per m/s wheel speed) */

    /* State */
    double x, y;        /* position (m) */
    double vx, vy;      /* velocity (m/s) */
    double heading;     /* = trapezoidal integral of omega (rad) */
    double omega;       /* angular velocity (rad/s) */
    float  alpha;       /* angular acceleration (rad/s^2) */
    float  prev_omega;  /* for alpha finite-difference */
    float  u_a, u_b;    /* ESC-lagged applied throttles */

    imu_synth_t synth;
};

void plant_params_default(plant_params_t *p) {
    /* Anchored to the real robot; see docs/firmware.md section 5. */
    p->mass_kg         = 0.454f;   /* 1 lb */
    p->body_radius_m   = 0.085f;   /* 170mm body diameter */
    p->tip_radius_m    = 0.115f;   /* 230mm tip-to-tip, collision radius */
    p->inertia_factor  = 0.55f;    /* mass distribution (solid disc = 0.5) */

    p->motor_offset_m  = 0.055f;   /* drive-wheel lever from centre */
    p->omega_free      = 419.0f;   /* ~4000 rpm terminal at full throttle */
    p->spin_tau_s      = 0.7f;     /* ~2s to near-terminal */
    p->esc_tau_s       = 0.003f;   /* ESC/motor response; must be << rev period
                                    * or per-rev drift modulation is filtered
                                    * out (this is why authority falls at very
                                    * high RPM, matching community reports) */

    p->floor_mu        = 0.35f;    /* Coulomb translation friction */
    p->floor_viscous   = 0.4f;     /* small linear damping */
    p->arena_half_m    = 0.9f;     /* ~1.8m square arena */
    p->wall_restitution= 0.35f;
    p->wall_mu         = 0.5f;
}

/* Derive the per-motor force curve so that:
 *   - terminal omega at full throttle == omega_free
 *   - the spin-up first-order time constant == spin_tau_s
 * Net spin torque (balanced) is  tau = C1*u - C2*omega, with
 *   C2 = I / spin_tau,  C1 = C2 * omega_free.
 * At the per-motor level tau = r_w*(F_a+F_b) and F_i = Fs*u_i - Kb*(omega*r_w),
 * giving Fs = C1/(2*r_w) and Kb = C2/(2*r_w^2). */
static void recompute_motor(plant_t *p) {
    const plant_params_t *m = &p->prm;
    p->inertia = m->inertia_factor * m->mass_kg * m->body_radius_m * m->body_radius_m;
    float rw = m->motor_offset_m;
    float c2 = p->inertia / m->spin_tau_s;
    float c1 = c2 * m->omega_free;
    p->motor_fs = c1 / (2.0f * rw);
    p->motor_kb = c2 / (2.0f * rw * rw);
}

plant_t *plant_create_params(uint64_t seed, const plant_params_t *params) {
    plant_t *p = calloc(1, sizeof(plant_t));
    if (!p) return NULL;
    p->prm = *params;
    recompute_motor(p);
    imu_synth_init(&p->synth, seed);
    plant_reset(p);
    return p;
}

plant_t *plant_create(uint64_t seed) {
    plant_params_t d;
    plant_params_default(&d);
    return plant_create_params(seed, &d);
}

void plant_destroy(plant_t *p) {
    free(p);
}

void plant_reset(plant_t *p) {
    p->x = p->y = 0.0;
    p->vx = p->vy = 0.0;
    p->heading = 0.0;
    p->omega = 0.0;
    p->alpha = 0.0f;
    p->prev_omega = 0.0f;
    p->u_a = p->u_b = 0.0f;
}

/* Per-motor tangential force from applied throttle and current spin.
 * Back-EMF (Kb*wheel_speed) is identical for both wheels (same radius,
 * same omega), so it cancels in the A-B difference that drives
 * translation while still limiting terminal RPM in the A+B sum. */
static float motor_force(const plant_t *p, float u) {
    float v_wheel = (float)p->omega * p->prm.motor_offset_m;
    float f = p->motor_fs * u - p->motor_kb * v_wheel;
    if (f >  p->motor_fs) f =  p->motor_fs;
    if (f < -p->motor_fs) f = -p->motor_fs;
    return f;
}

/* Handle all four arena walls. Circle centre at (x,y), radius tip_radius.
 * Each wall contributes an inward normal n and a penetration depth when the
 * disc overlaps it. For each: push out, apply normal restitution, then a
 * friction-cone tangential impulse that launches the disc along the wall
 * (skitter) and bleeds spin. */
static void collide_walls(plant_t *p) {
    float a = p->prm.arena_half_m;
    float R = p->prm.tip_radius_m;
    float e = p->prm.wall_restitution;
    float mu = p->prm.wall_mu;
    float m = p->prm.mass_kg;
    float I = p->inertia;

    float wnx[4], wny[4], wpen[4];
    int nw = 0;
    if (p->x + R > a)  { wnx[nw] = -1.0f; wny[nw] = 0.0f; wpen[nw] = (float)(p->x + R - a); nw++; }
    if (p->x - R < -a) { wnx[nw] =  1.0f; wny[nw] = 0.0f; wpen[nw] = (float)(-a - (p->x - R)); nw++; }
    if (p->y + R > a)  { wnx[nw] = 0.0f; wny[nw] = -1.0f; wpen[nw] = (float)(p->y + R - a); nw++; }
    if (p->y - R < -a) { wnx[nw] = 0.0f; wny[nw] =  1.0f; wpen[nw] = (float)(-a - (p->y - R)); nw++; }

    for (int i = 0; i < nw; i++) {
        float nx = wnx[i], ny = wny[i], pen = wpen[i];

        /* Push out of penetration along the inward normal. */
        p->x += (double)nx * pen;
        p->y += (double)ny * pen;

        /* Normal velocity component (into wall is negative along n). */
        float vn = (float)p->vx * nx + (float)p->vy * ny;
        if (vn < 0.0f) {
            /* Normal restitution impulse. */
            float jn = -(1.0f + e) * vn * m;   /* >=0 */
            p->vx += (double)(jn / m) * nx;
            p->vy += (double)(jn / m) * ny;

            /* Tangent direction (rotate normal +90 deg). */
            float tx = -ny, ty = nx;
            /* Surface velocity at the contact point = translational tangential
             * component + rim speed from spin. Contact point sits at -n*R from
             * centre; its spin velocity is omega * (z x (-n*R)). */
            float vt = (float)p->vx * tx + (float)p->vy * ty;
            float v_rim = (float)p->omega * R;   /* signed along +t for +omega */
            float v_surf = vt + v_rim;

            /* Friction impulse opposes surface tangential velocity, clamped
             * to the Coulomb cone mu*jn. */
            float jt = -m * v_surf;
            float jt_max = mu * jn;
            if (jt >  jt_max) jt =  jt_max;
            if (jt < -jt_max) jt = -jt_max;

            /* Skitter: apply tangential impulse to translation. */
            p->vx += (double)(jt / m) * tx;
            p->vy += (double)(jt / m) * ty;

            /* Spin bleed: reaction torque of the friction impulse at radius R.
             * The impulse acts along +t at the contact point -n*R; its moment
             * about the centre is (-n*R) x (jt*t) = -jt*R (scalar, z). */
            p->omega += (double)(-jt * R / I);
        }
    }
}

void plant_step(plant_t *p, float throttle_a, float throttle_b, float dt) {
    if (throttle_a < 0.0f) throttle_a = 0.0f;
    if (throttle_a > 1.0f) throttle_a = 1.0f;
    if (throttle_b < 0.0f) throttle_b = 0.0f;
    if (throttle_b > 1.0f) throttle_b = 1.0f;

    /* First-order ESC lag toward the commanded throttles. */
    float esc_a = dt / (p->prm.esc_tau_s + dt);
    p->u_a += (throttle_a - p->u_a) * esc_a;
    p->u_b += (throttle_b - p->u_b) * esc_a;

    float fa = motor_force(p, p->u_a);
    float fb = motor_force(p, p->u_b);
    float rw = p->prm.motor_offset_m;

    /* Spin torque: both wheels push in the +spin sense. */
    float torque = rw * (fa + fb);
    p->omega += (double)(torque / p->inertia) * dt;

    /* Body-frame net translation force = (0, fb - fa); rotate to world by
     * heading. */
    float h = (float)p->heading;
    float ch = cosf(h), sh = sinf(h);
    float fnet = fb - fa;                 /* along body +y */
    float fx = -sh * fnet;                /* R(h)*(0,fnet) */
    float fy =  ch * fnet;

    /* Coulomb + viscous floor friction opposing translation. */
    float m = p->prm.mass_kg;
    float speed = sqrtf((float)(p->vx * p->vx + p->vy * p->vy));
    if (speed > 1e-6f) {
        float coulomb = p->prm.floor_mu * m * GRAVITY;
        float fxn = (float)p->vx / speed, fyn = (float)p->vy / speed;
        fx -= coulomb * fxn;
        fy -= coulomb * fyn;
    }
    fx -= p->prm.floor_viscous * m * (float)p->vx;
    fy -= p->prm.floor_viscous * m * (float)p->vy;

    /* Semi-implicit integrate velocity then position. */
    p->vx += (double)(fx / m) * dt;
    p->vy += (double)(fy / m) * dt;

    /* Stop Coulomb friction from reversing a nearly-stopped body. */
    float nspeed = sqrtf((float)(p->vx * p->vx + p->vy * p->vy));
    if (nspeed < 1e-3f && fnet == 0.0f) { p->vx = 0.0; p->vy = 0.0; }

    p->x += p->vx * dt;
    p->y += p->vy * dt;

    /* Heading = trapezoidal integral of omega (matches EKF midpoint predict). */
    p->heading += 0.5 * ((double)p->prev_omega + p->omega) * dt;

    collide_walls(p);

    p->alpha = (dt > 0.0f) ? ((float)p->omega - p->prev_omega) / dt : 0.0f;
    p->prev_omega = (float)p->omega;
}

void plant_kick_omega(plant_t *p, float domega) {
    p->omega += (double)domega;
}

void plant_set_pose(plant_t *p, float x, float y, float vx, float vy) {
    p->x = x;  p->y = y;
    p->vx = vx; p->vy = vy;
}

imu_synth_t *plant_synth(plant_t *p) {
    return &p->synth;
}

void plant_read_imu(plant_t *p, mat_t *z, float dt) {
    imu_synth_read(&p->synth, (float)p->omega, p->alpha, dt, z);
}

float plant_true_heading(const plant_t *p) {
    return wrap_0_2pi((float)p->heading);
}

float plant_true_omega(const plant_t *p) {
    return (float)p->omega;
}

float plant_true_alpha(const plant_t *p) {
    return p->alpha;
}

void plant_position(const plant_t *p, float *x, float *y) {
    *x = (float)p->x;
    *y = (float)p->y;
}

float plant_arena_size(const plant_t *p) {
    return p->prm.arena_half_m;
}

float plant_body_radius(const plant_t *p) {
    return p->prm.body_radius_m;
}

float plant_tip_radius(const plant_t *p) {
    return p->prm.tip_radius_m;
}
