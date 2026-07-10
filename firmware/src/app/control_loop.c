#include "control_loop.h"

#include "math/linalg.h"
#include "estimation/imu_convert.h"
#include "estimation/accel_cal.h"
#include "control/pid.h"

/* PID state is module-level runtime state, not config. This keeps the
 * shared config struct clean (serializable, no mutable state) and
 * prevents callers from reaching into PID internals. */
static pid_t rpm_pid;

/* dt guard: if timestep is outside this band, fall back to CONTROL_DT. */
#define DT_MIN 0.0f
#define DT_MAX 0.1f

app_estimate_t app_sensor_tick(ekf_t *ekf, const imu_sample_t samples[IMU_COUNT],
                               float dt) {
    mat_t z;
    imu_samples_to_meas(samples, &z);
    return app_sensor_tick_si(ekf, &z, dt);
}

app_estimate_t app_sensor_tick_si(ekf_t *ekf, const mat_t *z, float dt) {
    if (dt <= DT_MIN || dt > DT_MAX) dt = CONTROL_DT;

    /* Apply the accelerometer nonlinearity correction before the filter
     * sees the measurement. No-op until a cal table is loaded; on hardware
     * this is the H3LIS near-saturation correction that keeps heading from
     * dead-reckoning off during translation. */
    mat_t zc = *z;
    accel_cal_apply(&zc);

    ekf_predict(ekf, dt);
    ekf_update(ekf, &zc);

    app_estimate_t est;
    est.heading = ekf_heading_wrapped(ekf);
    est.omega = ekf_omega(ekf);
    est.alpha = ekf_alpha(ekf);
    return est;
}

app_motors_t app_control_tick(app_config_t *cfg, const app_command_t *cmd,
                              const app_estimate_t *est, float dt) {
    app_motors_t out;

    /* Guard against a bad measured period (first tick, scheduler hiccup). */
    if (dt <= DT_MIN || dt > DT_MAX) dt = CONTROL_DT;

    if (!cmd->armed) {
        pid_reset(&rpm_pid);
        out.throttle_a = 0.0f;
        out.throttle_b = 0.0f;
        return out;
    }

    /* Compute base throttle: either PID-regulated or direct from stick. */
    float base = cmd->base;
    if (cfg->pid_enabled) {
        float target_rpm = cmd->base * cfg->target_rpm_max;
        float current_rpm = est->omega * RAD_S_TO_RPM;
        base = pid_compute(&rpm_pid, target_rpm, current_rpm, dt);
    }

    if (!cfg->drift_enabled) {
        out.throttle_a = base;
        out.throttle_b = base;
        return out;
    }

    float authority, phi;
    drift_from_stick(cmd->stick_x, cmd->stick_y, cfg->max_authority,
                     &authority, &phi);
    float heading = est->heading - cfg->heading_trim;
    phi -= cfg->drift_phase;
    drift_throttles_t d = drift_compute(heading, base, authority, phi, cfg->mod_mode);
    out.throttle_a = d.a;
    out.throttle_b = d.b;
    return out;
}

void app_pid_reset(void) {
    pid_reset(&rpm_pid);
}

void app_config_default(app_config_t *cfg) {
    cfg->max_authority = 0.5f;
    cfg->drift_enabled = false;
    cfg->heading_trim = 0.0f;
    cfg->drift_phase = -0.225f;
    cfg->pid_enabled = false;
    cfg->target_rpm_max = 3000.0f;
    cfg->mod_mode = DRIFT_DEFAULT_MODE;
    /* Initialize module-level PID with conservative gains. */
    pid_init(&rpm_pid, 0.002f, 0.001f, 0.0f, 0.0f, 1.0f);
}
