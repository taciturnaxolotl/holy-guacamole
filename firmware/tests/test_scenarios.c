#include "test_assert.h"

#include "estimation/ekf.h"
#include "estimation/meas_model.h"
#include "estimation/imu_geom.h"
#include "estimation/accel_cal.h"
#include "app/control_loop.h"
#include "plant.h"

#include <math.h>

/*
 * Closed-loop SITL scenarios: the REAL estimator + controller
 * (app_sensor_tick_si + app_control_tick) driven against the hand-rolled
 * plant, with assertions on emergent behaviour. This is the digital-twin
 * regression layer -- it exercises physics + firmware together, where the
 * unit tests exercise modules in isolation.
 */

#define DT 0.001f  /* 1 kHz control/physics tick */
#define RPM(w) ((w) * 60.0f / (2.0f * (float)M_PI))

/* One closed-loop tick: sense -> estimate -> control -> actuate. */
static heading_estimate_t g_est;
static void tick(plant_t *p, ekf_t *e, app_config_t *cfg, app_command_t *cmd) {
    mat_t z;
    plant_read_imu(p, &z, DT);
    g_est = app_sensor_tick_si(e, &z, DT);
    app_motors_t m = app_control_tick(cfg, cmd, &g_est, DT);
    plant_step(p, m.throttle_a, m.throttle_b, DT);
}

/* Open-loop spin to a target base throttle for a given time. */
static void spin(plant_t *p, ekf_t *e, app_config_t *cfg, float base, float secs) {
    app_command_t cmd = {0};
    cmd.armed = true;
    cmd.base = base;
    int n = (int)(secs / DT);
    for (int i = 0; i < n; i++) tick(p, e, cfg, &cmd);
}

/* Scenario 1: spin-up reaches the anchored terminal RPM, the EKF tracks
 * omega through it, and the gyro is confirmed railed at speed. */
static void scenario_spinup(void) {
    plant_t *p = plant_create(0xA11CE);
    ekf_t e; ekf_init(&e, 0.0f);
    app_config_t cfg; app_config_default(&cfg);

    /* ~0.65 throttle reaches combat RPM (full throttle terminal is much
     * higher, leaving headroom for drift modulation). */
    spin(p, &e, &cfg, 0.65f, 3.0f);

    float w = plant_true_omega(p);
    ASSERT_TRUE(RPM(w) > 3600.0f && RPM(w) < 4200.0f);
    ASSERT_TRUE(fabsf(g_est.omega - w) < 0.05f * w);

    /* The gyro must be pinned to its rail at combat RPM. */
    mat_t z; plant_read_imu(p, &z, DT);
    ASSERT_TRUE(fabsf(mat_get(&z, MEAS_A_GYRO, 0)) >= 0.98f * GYRO_FULL_SCALE_RADS);

    plant_destroy(p);
}

/* Scenario 2: at cruise, commanding a drift direction actually translates
 * the robot, and the omega estimate stays locked during the manoeuvre.
 * Sensor is calibrated (nonlinearity removed, as accel_cal would). */
static void scenario_cruise_drift(void) {
    plant_t *p = plant_create(0xBEE5);
    plant_synth(p)->enable_nonlinearity = false;
    ekf_t e; ekf_init(&e, 0.0f);
    app_config_t cfg; app_config_default(&cfg);

    spin(p, &e, &cfg, 0.44f, 2.0f);  /* reach ~2700 rpm */

    float x0, y0; plant_position(p, &x0, &y0);
    cfg.drift_enabled = true;
    app_command_t cmd = {0};
    cmd.armed = true; cmd.base = 0.44f; cmd.stick_x = 1.0f; cmd.stick_y = 0.0f;
    for (int i = 0; i < 1500; i++) tick(p, &e, &cfg, &cmd);

    float x1, y1; plant_position(p, &x1, &y1);
    float disp = sqrtf((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0));
    ASSERT_TRUE(disp > 0.1f);  /* it drifted */

    float w = plant_true_omega(p);
    ASSERT_TRUE(fabsf(g_est.omega - w) < 0.03f * w);  /* lock held */

    plant_destroy(p);
}

/* Scenario 3: a spinning disc driven into a wall bounces (normal
 * restitution), skitters along it (spin->tangential coupling), and loses
 * RPM (spin bleed). Driven at the plant directly for a deterministic,
 * motor-free contact. */
static void scenario_wall_skitter(void) {
    plant_t *p = plant_create(0x5AFE);
    plant_set_pose(p, 0.7f, 0.0f, 1.5f, 0.0f);  /* moving +x toward wall */
    plant_kick_omega(p, 300.0f);                 /* fast +spin */

    float w_before = plant_true_omega(p);

    /* Coast (zero throttle, no drive) into the wall so any tangential
     * motion can only come from rim-wall friction, not the motors. */
    for (int i = 0; i < 250; i++) plant_step(p, 0.0f, 0.0f, DT);

    /* Velocity via a one-step finite difference. */
    float xa, ya; plant_position(p, &xa, &ya);
    plant_step(p, 0.0f, 0.0f, DT);
    float xb, yb; plant_position(p, &xb, &yb);
    float vx_after = (xb - xa) / DT;
    float vy_after = (yb - ya) / DT;
    float w_after = plant_true_omega(p);

    ASSERT_TRUE(vx_after < 0.0f);              /* bounced back off +x wall */
    ASSERT_TRUE(fabsf(vy_after) > 0.05f);      /* skittered along the wall */
    ASSERT_TRUE(w_after < w_before);           /* bled spin on contact */

    plant_destroy(p);
}

/* Scenario 4: uncorrected H3LIS nonlinearity walks heading badly; the
 * calibrated sensor holds far better. Guards the finding that accel_cal
 * is mandatory (see docs/firmware.md section 6). */
static float cruise_heading_drift(uint64_t seed, bool nonlinearity) {
    plant_t *p = plant_create(seed);
    plant_synth(p)->enable_nonlinearity = nonlinearity;
    ekf_t e; ekf_init(&e, 0.0f);
    app_config_t cfg; app_config_default(&cfg);

    spin(p, &e, &cfg, 0.44f, 2.0f);  /* reach cruise, gyro bootstraps sign */

    float err0 = g_est.heading - plant_true_heading(p);
    float maxdrift = 0.0f;
    app_command_t cmd = {0};
    cmd.armed = true; cmd.base = 0.44f;
    for (int i = 0; i < 3000; i++) {
        tick(p, &e, &cfg, &cmd);
        float d = (g_est.heading - plant_true_heading(p)) - err0;
        while (d > (float)M_PI)  d -= 2.0f * (float)M_PI;
        while (d < -(float)M_PI) d += 2.0f * (float)M_PI;
        if (fabsf(d) > maxdrift) maxdrift = fabsf(d);
    }
    plant_destroy(p);
    return maxdrift;
}

static void scenario_nonlinearity_matters(void) {
    accel_cal_clear();
    float calibrated = cruise_heading_drift(0xCA11B, false);
    float raw        = cruise_heading_drift(0xCA11B, true);
    ASSERT_TRUE(calibrated < 1.0f);        /* calibrated holds (<~57 deg/3s) */
    ASSERT_TRUE(raw > calibrated + 0.5f);  /* uncorrected is markedly worse */
}

/* Scenario 4b: wiring accel_cal into the estimation path recovers heading.
 * With the H3LIS nonlinearity ON, loading the inverse correction curve
 * (what a bench spin-up sweep would produce) brings heading drift back down
 * toward the calibrated case -- the whole point of the module. */
static void scenario_accel_cal_recovers_heading(void) {
    accel_cal_clear();
    float uncorrected = cruise_heading_drift(0xACCE1, true);  /* nonlin, no cal */

    /* Inverse of the sim's model: reading *= (1 - k*(g/FS)^2), k=0.05,
     * FS=400g, so the correction factor is 1/(1 - k*(g/FS)^2). Load it into
     * both outer H3LIS (IMU-B and IMU-C, which carry the nonlinearity). */
    for (int i = 0; i <= 4; i++) {
        float g = (float)i * 100.0f;          /* 0,100,200,300,400 g */
        float x = g / 400.0f;
        float f = 1.0f / (1.0f - 0.05f * x * x);
        accel_cal_add(ACCEL_CAL_IMU_B, g, f);
        accel_cal_add(ACCEL_CAL_IMU_C, g, f);
    }
    float corrected = cruise_heading_drift(0xACCE1, true);   /* nonlin + cal */
    accel_cal_clear();

    ASSERT_TRUE(corrected < uncorrected);          /* the correction helps */
    ASSERT_TRUE(corrected < 0.5f * uncorrected);   /* and helps a lot */
}

/* Scenario 5: at burst overspeed the gyro AND both outer H3LIS radial
 * channels rail, while the inner LSM6 accel stays in-spec -- the
 * mixed-radius design's whole point. */
static void scenario_burst_saturation(void) {
    plant_t *p = plant_create(0x6057);
    plant_kick_omega(p, 490.0f);  /* ~4680 rpm, above the outer G ceiling */

    mat_t z; plant_read_imu(p, &z, DT);
    bool sat[MEAS_DIM];
    meas_saturation_flags(&z, sat);

    ASSERT_TRUE(sat[MEAS_A_GYRO]);      /* gyro railed */
    ASSERT_TRUE(sat[MEAS_B_RADIAL]);    /* outer railed */
    ASSERT_TRUE(sat[MEAS_C_RADIAL]);
    ASSERT_TRUE(!sat[MEAS_A_RADIAL]);   /* inner still in-spec */

    plant_destroy(p);
}

int main(void) {
    RUN_TEST(scenario_spinup);
    RUN_TEST(scenario_cruise_drift);
    RUN_TEST(scenario_wall_skitter);
    RUN_TEST(scenario_nonlinearity_matters);
    RUN_TEST(scenario_accel_cal_recovers_heading);
    RUN_TEST(scenario_burst_saturation);
    return test_report();
}
