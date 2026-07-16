#include "pid.h"

void pid_init(pid_t *p, float kp, float ki, float kd,
              float out_min, float out_max) {
    p->kp = kp;
    p->ki = ki;
    p->kd = kd;
    p->integral = 0.0f;
    p->prev_error = 0.0f;
    p->out_min = out_min;
    p->out_max = out_max;
}

static float clamp(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

float pid_compute(pid_t *p, float setpoint, float measurement, float dt) {
    if (dt <= 0.0f) return 0.0f;

    float error = setpoint - measurement;

    /* Proportional */
    float p_term = p->kp * error;

    /* Integral with anti-windup: clamp integrator to output range / ki
     * so it can't accumulate beyond what the output can express. */
    p->integral += error * dt;
    float i_max = (p->ki > 0.0f) ? (p->out_max / p->ki) : 1.0f;
    p->integral = clamp(p->integral, -i_max, i_max);
    float i_term = p->ki * p->integral;

    /* Derivative on error */
    float d_term = p->kd * (error - p->prev_error) / dt;
    p->prev_error = error;

    float output = p_term + i_term + d_term;

    return clamp(output, p->out_min, p->out_max);
}

void pid_reset(pid_t *p) {
    p->integral = 0.0f;
    p->prev_error = 0.0f;
}
