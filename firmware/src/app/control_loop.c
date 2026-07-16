#include "control_loop.h"

#include "math/linalg.h"
#include "control/pid.h"

#if defined(SENSOR_SOURCE_IMU_EKF)
#include "estimation/imu_convert.h"
#include "estimation/accel_cal.h"
#endif

/* PID state is module-level runtime state, not config. This keeps the
 * shared config struct clean (serializable, no mutable state) and
 * prevents callers from reaching into PID internals. */
static pid_t rpm_pid;

/* dt guard: if timestep is outside this band, fall back to CONTROL_DT. */
#define DT_MIN 0.0f
#define DT_MAX 0.1f

#if defined(SENSOR_SOURCE_IMU_EKF)
heading_estimate_t app_sensor_tick(ekf_t *ekf, const imu_sample_t samples[IMU_COUNT],
                               float dt) {
    mat_t z;
    imu_samples_to_meas(samples, &z);
    return app_sensor_tick_si(ekf, &z, dt);
}

heading_estimate_t app_sensor_tick_si(ekf_t *ekf, const mat_t *z, float dt) {
    if (dt <= DT_MIN || dt > DT_MAX) dt = CONTROL_DT;

    mat_t zc = *z;
    accel_cal_apply(&zc);

    ekf_predict(ekf, dt);
    ekf_update(ekf, &zc);

    heading_estimate_t est;
    est.heading = ekf_heading_wrapped(ekf);
    est.omega = ekf_omega(ekf);
    est.alpha = ekf_alpha(ekf);
    return est;
}
#endif

app_motors_t app_control_tick(app_config_t *cfg, const app_command_t *cmd,
                              const heading_estimate_t *est, float dt) {
    app_motors_t out;

    if (dt <= DT_MIN || dt > DT_MAX) dt = CONTROL_DT;

    /* Mode gate: STOP = all motors off regardless of anything else. */
    if (!cmd->armed || cmd->mode == DRIVE_MODE_STOP) {
        pid_reset(&rpm_pid);
        out.throttle_a = 0.0f;
        out.throttle_b = 0.0f;
        return out;
    }

    /* Determine target RPM from discrete speed level or attack button. */
    float target_rpm = 0.0f;
    if (cmd->attack) {
        target_rpm = cfg->rpm_attack;
    } else {
        switch (cmd->speed) {
            case SPEED_LOW:  target_rpm = cfg->rpm_low;  break;
            case SPEED_MED:  target_rpm = cfg->rpm_med;  break;
            case SPEED_HIGH: target_rpm = cfg->rpm_high; break;
            case SPEED_OFF:
            default:         target_rpm = 0.0f;          break;
        }
    }

    /* If no speed target, fall back to analog base throttle. */
    float base;
    if (target_rpm > 0.0f && cfg->pid_enabled) {
        float current_rpm = est->omega * RAD_S_TO_RPM;
        base = pid_compute(&rpm_pid, target_rpm, current_rpm, dt);
    } else if (target_rpm > 0.0f) {
        /* PID disabled but speed level set: map level to fixed throttle. */
        base = target_rpm / cfg->target_rpm_max;
        if (base > 1.0f) base = 1.0f;
    } else {
        base = cmd->base;
    }

    /* Spin-only mode: equal throttle, no drift. */
    if (cmd->mode == DRIVE_MODE_SPIN) {
        out.throttle_a = base;
        out.throttle_b = base;
        return out;
    }

    /* Drift mode. */
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
    cfg->target_rpm_max = 4250.0f;
    cfg->mod_mode = DRIFT_DEFAULT_MODE;
    cfg->rpm_low = 1000.0f;
    cfg->rpm_med = 2000.0f;
    cfg->rpm_high = 2750.0f;
    cfg->rpm_attack = 4250.0f;
    pid_init(&rpm_pid, 0.002f, 0.001f, 0.0f, 0.0f, 1.0f);
}
