#include "robot_sim.h"
#include "imu_synth.h"

void sim_init(robot_sim_t *s, double omega0, uint64_t seed) {
    s->theta = 0.0;
    s->omega = omega0;
    s->alpha = 0.0;
    imu_synth_init(&s->synth, seed);
}

void sim_step(robot_sim_t *s, double alpha_cmd, double dt) {
    s->alpha = alpha_cmd;
    s->theta += s->omega * dt + 0.5 * s->alpha * dt * dt;
    s->omega += s->alpha * dt;
}

void sim_kick_omega(robot_sim_t *s, double domega) {
    s->omega += domega;
}

void sim_read(robot_sim_t *s, mat_t *z, double dt) {
    imu_synth_read(&s->synth, (float)s->omega, (float)s->alpha, (float)dt, z);
}
