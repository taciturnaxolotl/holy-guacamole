#pragma once

/*
 * Shared per-tick application logic, free of hardware dependencies.
 *
 * Both the firmware (main.c, split across two cores) and the SITL
 * simulator call these exact functions. This is the "run the real code"
 * surface: EKF estimation and drift control live here, while the
 * hardware plumbing (SPI/PIO/DMA/multicore) stays in the callers.
 */

#include <stdint.h>
#include <stdbool.h>

#include "estimation/heading_estimate.h"
#include "control/drift.h"

#if defined(SENSOR_SOURCE_IMU_EKF)
#include "imu/imu_spi.h"
#include "estimation/ekf.h"
#endif

/* rad/s → RPM conversion factor. */
#define RAD_S_TO_RPM 9.5493f

/* Control loop timestep in seconds. Must match the sleep in core 1. */
#define CONTROL_DT 0.0005f

/* Drift modulation mode selected at BUILD time (there is no runtime toggle
 * by design). Flip this line to DRIFT_MOD_SQUARE, or configure the build
 * with -DDRIFT_DEFAULT_MODE=DRIFT_MOD_SQUARE, to ship a square-wave robot. */
#ifndef DRIFT_DEFAULT_MODE
#define DRIFT_DEFAULT_MODE DRIFT_MOD_SINUSOIDAL
#endif

/* Drive mode selected by the safety/mode switch. */
typedef enum {
    DRIVE_MODE_STOP = 0,     /* all stop, motors disabled */
    DRIVE_MODE_SPIN = 1,     /* spin only, no drift translation */
    DRIVE_MODE_DRIFT = 2,    /* full meltybrain drift */
} drive_mode_t;

/* Discrete speed levels (Liftoff-style). */
typedef enum {
    SPEED_OFF   = 0,
    SPEED_LOW   = 1,
    SPEED_MED   = 2,
    SPEED_HIGH  = 3,
} speed_level_t;

/* RC command inputs, normalized. */
typedef struct {
    float base;          /* symmetric throttle [0,1] (analog fallback) */
    float stick_x;       /* drift vector x [-1,1] */
    float stick_y;       /* drift vector y [-1,1] */
    bool  armed;         /* link alive and safe to drive */
    drive_mode_t mode;   /* STOP / SPIN / DRIFT */
    speed_level_t speed; /* OFF / LOW / MED / HIGH */
    bool  attack;        /* momentary attack RPM button held */
    bool  spin_cw;       /* true=CW, false=CCW */
} app_command_t;

/* Motor outputs. */
typedef struct {
    float throttle_a;
    float throttle_b;
} app_motors_t;

/* Tunables shared by both callers. PID state is intentionally NOT here;
 * it's runtime state managed internally by control_loop.c. */
typedef struct {
    float max_authority;      /* drift authority cap [0,1] */
    bool  drift_enabled;      /* false = open-loop spin (motors follow base) */
    float heading_trim;       /* rad subtracted from estimated heading so the
                                 operator can align "forward"; heading is not
                                 absolutely observable, so this is a stored
                                 alignment constant (set by eye on the robot). */
    float drift_phase;        /* rad; residual drive-phase calibration after
                                 geometric +90 deg compensation in drift_compute.
                                 0 nominal; bench-tune per robot. */
    bool  pid_enabled;        /* true = PID regulates RPM from stick; false = direct throttle */
    float target_rpm_max;     /* RPM at full stick deflection when PID enabled */
    drift_mod_t mod_mode;     /* DRIFT_MOD_SINUSOIDAL or DRIFT_MOD_SQUARE */

    /* Discrete speed levels (RPM targets). */
    float rpm_low;            /* SPEED_LOW target RPM */
    float rpm_med;            /* SPEED_MED target RPM */
    float rpm_high;           /* SPEED_HIGH target RPM */
    float rpm_attack;         /* attack button override RPM */
} app_config_t;

#if defined(SENSOR_SOURCE_IMU_EKF)
/* Sensor-side tick: run the EKF on one IMU sample set over dt seconds
 * and return the current estimate. */
heading_estimate_t app_sensor_tick(ekf_t *ekf, const imu_sample_t samples[IMU_COUNT],
                               float dt);

/* Sensor-side core operating directly on an SI measurement vector
 * (m/s^2, rad/s). app_sensor_tick calls this after raw-count conversion;
 * the SITL sim calls it directly, so both run the identical EKF path. */
heading_estimate_t app_sensor_tick_si(ekf_t *ekf, const mat_t *z, float dt);
#endif

/* Control-side tick: turn RC command + latest estimate into motor
 * throttles using the drift controller. dt is the time since last call
 * (for PID integration). */
app_motors_t app_control_tick(app_config_t *cfg, const app_command_t *cmd,
                              const heading_estimate_t *est, float dt);

/* Reset PID state (e.g., on disarm or mode change). */
void app_pid_reset(void);

/* Sensible defaults. */
void app_config_default(app_config_t *cfg);
