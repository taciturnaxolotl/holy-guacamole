#include "app/control_loop.h"

#include "math/linalg.h"
#include "estimation/imu_convert.h"

app_estimate_t app_sensor_tick(ekf_t *ekf, const imu_sample_t samples[IMU_COUNT],
                               float dt) {
    mat_t z;
    imu_samples_to_meas(samples, &z);
    return app_sensor_tick_si(ekf, &z, dt);
}

app_estimate_t app_sensor_tick_si(ekf_t *ekf, const mat_t *z, float dt) {
    if (dt <= 0.0f || dt > 0.1f) dt = 0.001f;  /* guard bad deltas */

    ekf_predict(ekf, dt);
    ekf_update(ekf, z);

    app_estimate_t est;
    est.heading = ekf_heading_wrapped(ekf);
    est.omega = ekf_omega(ekf);
    est.alpha = ekf_alpha(ekf);
    return est;
}

app_motors_t app_control_tick(const app_config_t *cfg, const app_command_t *cmd,
                              const app_estimate_t *est) {
    app_motors_t out;

    if (!cmd->armed) {
        out.throttle_a = 0.0f;
        out.throttle_b = 0.0f;
        return out;
    }

    if (!cfg->drift_enabled) {
        /* Open-loop spin: both motors follow the base throttle. */
        out.throttle_a = cmd->base;
        out.throttle_b = cmd->base;
        return out;
    }

    float authority, phi;
    drift_from_stick(cmd->stick_x, cmd->stick_y, cfg->max_authority,
                     &authority, &phi);
    /* Add the drive-phase calibration: motor thrust is tangential, a
     * quarter turn off the radial heading, so net translation lags the
     * modulation peak by ~90 deg. Fold that plus the stored heading trim
     * into the modulation phase so a commanded world direction actually
     * translates that way. drift_phase is refined per-robot on the bench. */
    float heading = est->heading - cfg->heading_trim;
    phi -= cfg->drift_phase;
    drift_throttles_t d = drift_compute(heading, cmd->base, authority, phi);
    out.throttle_a = d.a;
    out.throttle_b = d.b;
    return out;
}

void app_config_default(app_config_t *cfg) {
    cfg->max_authority = 0.5f;
    cfg->drift_enabled = false;  /* bring-up safe default: open-loop */
    cfg->heading_trim = 0.0f;
    cfg->drift_phase = -0.225f; /* residual heading-lag calibration (bench-tune per robot) */
}
