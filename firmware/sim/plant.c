#include "plant.h"
#include "imu_synth.h"
#include "estimation/imu_geom.h"

#include <stdlib.h>
#include <math.h>
#include "box2d/box2d.h"

/* --- Tunable plant constants (guesses until real telemetry) --- */
#define DISC_RADIUS_M     0.075f   /* 150mm chassis */
#define DISC_DENSITY      26.0f    /* kg/m^2 areal -> ~0.45kg antweight mass */
#define MOTOR_OFFSET_M    0.055f   /* wheel radius from centre (E/W) */
#define THRUST_MAX_N      6.0f     /* per-motor peak force at full throttle */
#define THRUST_GAMMA      1.3f     /* throttle->force curve exponent */
#define ANGULAR_DRAG      0.0012f  /* explicit drag torque coeff (N*m per rad/s) */
#define LINEAR_DAMPING    1.5f     /* floor friction / drag on translation */
#define ARENA_HALF_M      0.9f     /* ~1.8m square arena, half-extent */
#define WALL_RESTITUTION  0.4f
#define TWO_PI            6.28318530718f

struct plant {
    b2WorldId world;
    b2BodyId  disc;
    imu_synth_t synth;
    double heading;     /* authoritative heading = integral of reported omega */
    float prev_omega;   /* for alpha finite-difference */
    float alpha;        /* rad/s^2 */
};

/* Throttle -> force with a simple nonlinear thrust curve. */
static float thrust_curve(float throttle) {
    if (throttle <= 0.0f) return 0.0f;
    if (throttle > 1.0f) throttle = 1.0f;
    return THRUST_MAX_N * powf(throttle, THRUST_GAMMA);
}

static void add_wall(b2WorldId world, float cx, float cy, float hx, float hy) {
    b2BodyDef bd = b2DefaultBodyDef();
    bd.position = (b2Vec2){cx, cy};
    b2BodyId wall = b2CreateBody(world, &bd);  /* static by default */
    b2ShapeDef sd = b2DefaultShapeDef();
    sd.material.restitution = WALL_RESTITUTION;
    b2Polygon box = b2MakeBox(hx, hy);
    b2CreatePolygonShape(wall, &sd, &box);
}

plant_t *plant_create(uint64_t seed) {
    plant_t *p = calloc(1, sizeof(plant_t));
    if (!p) return NULL;

    b2WorldDef wd = b2DefaultWorldDef();
    wd.gravity = (b2Vec2){0.0f, 0.0f};  /* top-down */
    p->world = b2CreateWorld(&wd);

    /* Disc body. */
    b2BodyDef bd = b2DefaultBodyDef();
    bd.type = b2_dynamicBody;
    bd.position = (b2Vec2){0.0f, 0.0f};
    bd.linearDamping = LINEAR_DAMPING;
    /* No angularDamping: Box2D applies it mid-step, which makes the
     * reported angular velocity and the integrated rotation diverge at
     * high RPM. We model rotational drag as an explicit torque instead
     * so heading stays == integral of the reported omega. */
    p->disc = b2CreateBody(p->world, &bd);

    b2ShapeDef sd = b2DefaultShapeDef();
    sd.density = DISC_DENSITY;
    sd.material.restitution = WALL_RESTITUTION;
    b2Circle circle = {.center = {0.0f, 0.0f}, .radius = DISC_RADIUS_M};
    b2CreateCircleShape(p->disc, &sd, &circle);

    /* Arena walls (four static boxes around the square). */
    float a = ARENA_HALF_M;
    float t = 0.05f;  /* wall thickness */
    add_wall(p->world,  0.0f,  a + t, a + t, t);  /* top */
    add_wall(p->world,  0.0f, -a - t, a + t, t);  /* bottom */
    add_wall(p->world,  a + t, 0.0f, t, a + t);   /* right */
    add_wall(p->world, -a - t, 0.0f, t, a + t);   /* left */

    imu_synth_init(&p->synth, seed);
    p->prev_omega = 0.0f;
    p->alpha = 0.0f;
    return p;
}

void plant_destroy(plant_t *p) {
    if (!p) return;
    b2DestroyWorld(p->world);
    free(p);
}

void plant_reset(plant_t *p) {
    b2Body_SetTransform(p->disc, (b2Vec2){0.0f, 0.0f}, b2MakeRot(0.0f));
    b2Body_SetLinearVelocity(p->disc, (b2Vec2){0.0f, 0.0f});
    b2Body_SetAngularVelocity(p->disc, 0.0f);
    p->heading = 0.0;
    p->prev_omega = 0.0f;
    p->alpha = 0.0f;
}

void plant_step(plant_t *p, float throttle_a, float throttle_b, float dt) {
    float fa = thrust_curve(throttle_a);
    float fb = thrust_curve(throttle_b);

    /* Motors sit at local (-/+offset, 0) and push tangentially (local
     * -/+y). We rotate points and force directions by our OWN tracked
     * heading rather than Box2D's b2Rot: at meltybrain RPM (~23 deg per
     * step) Box2D's rotation state drifts from the omega it reports, so
     * we treat heading = integral of reported omega as truth. The disc
     * is a circle, so its Box2D orientation doesn't affect collisions. */
    float h = (float)p->heading;
    float ch = cosf(h), sh = sinf(h);
    b2Vec2 pos = b2Body_GetPosition(p->disc);

    /* local (-off,0) -> world offset; local dir (0,-1) -> world. */
    b2Vec2 pa = { pos.x - MOTOR_OFFSET_M * ch, pos.y - MOTOR_OFFSET_M * sh };
    b2Vec2 pb = { pos.x + MOTOR_OFFSET_M * ch, pos.y + MOTOR_OFFSET_M * sh };
    b2Vec2 da = { sh, -ch };   /* R(h) * (0,-1) */
    b2Vec2 db = { -sh, ch };   /* R(h) * (0, 1) */

    b2Body_ApplyForce(p->disc, (b2Vec2){da.x * fa, da.y * fa}, pa, true);
    b2Body_ApplyForce(p->disc, (b2Vec2){db.x * fb, db.y * fb}, pb, true);

    /* Explicit rotational drag torque. */
    float omega_now = b2Body_GetAngularVelocity(p->disc);
    b2Body_ApplyTorque(p->disc, -ANGULAR_DRAG * omega_now, true);

    b2World_Step(p->world, dt, 4);

    float omega = b2Body_GetAngularVelocity(p->disc);
    /* Trapezoidal heading integration (2nd order), matching the EKF's
     * midpoint predict so plant "truth" and estimator use the same
     * integration order and don't diverge by an integration artifact. */
    p->heading += 0.5 * ((double)p->prev_omega + (double)omega) * dt;
    p->alpha = (dt > 0.0f) ? (omega - p->prev_omega) / dt : 0.0f;
    p->prev_omega = omega;
}

void plant_read_imu(plant_t *p, mat_t *z) {
    float omega = b2Body_GetAngularVelocity(p->disc);
    imu_synth_read(&p->synth, omega, p->alpha, z);
}

float plant_true_heading(const plant_t *p) {
    return wrap_0_2pi((float)p->heading);
}

float plant_true_omega(const plant_t *p) {
    return b2Body_GetAngularVelocity(p->disc);
}

void plant_position(const plant_t *p, float *x, float *y) {
    b2Vec2 pos = b2Body_GetPosition(p->disc);
    *x = pos.x;
    *y = pos.y;
}

float plant_arena_size(const plant_t *p) {
    (void)p;
    return ARENA_HALF_M;
}
