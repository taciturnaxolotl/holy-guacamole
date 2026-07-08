#pragma once

/*
 * Simple PID controller for RPM regulation.
 *
 * Takes a target RPM (from stick) and current RPM (from EKF/eRPM),
 * outputs a throttle value [0, 1]. Used by core 1 to maintain consistent
 * spin speed regardless of battery sag or friction changes.
 *
 * Tuning: start with P only (Ki=Kd=0), increase until oscillation,
 * then back off ~30%. Add I to eliminate steady-state error. D is
 * rarely needed for RPM control.
 */

typedef struct {
    float kp, ki, kd;
    float integral;
    float prev_error;
    float out_min, out_max;
} pid_t;

void pid_init(pid_t *p, float kp, float ki, float kd,
              float out_min, float out_max);

/* Compute one PID step. dt in seconds. Returns clamped output. */
float pid_compute(pid_t *p, float setpoint, float measurement, float dt);

/* Reset integrator and derivative state (e.g., on mode change or disarm). */
void pid_reset(pid_t *p);
