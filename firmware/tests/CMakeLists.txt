# Native host test build for the pure (hardware-free) firmware modules.
# Separate from the RP2350 cross-compile: this builds with the host
# compiler so the EKF, drift, and math code can be validated on a Mac
# or Linux box with no target hardware.
#
# Usage:
#   cmake -B build-tests -S tests
#   cmake --build build-tests
#   ctest --test-dir build-tests --output-on-failure

cmake_minimum_required(VERSION 3.13)
project(holy_guacamole_tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

enable_testing()

# Pure modules under test. These must NOT include any pico/* headers.
set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../src)
set(SIM_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../sim)

# Build float32 math and warn hard: we want these clean.
add_compile_options(-Wall -Wextra -Werror -g -O2)

# Helper to declare a test executable linking the needed pure sources.
function(add_hg_test name)
    add_executable(${name} ${name}.c ${ARGN})
    target_include_directories(${name} PRIVATE ${SRC_DIR} ${SIM_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(${name} PRIVATE m)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

add_hg_test(test_linalg ${SRC_DIR}/math/linalg.c)

set(EKF_SRCS
    ${SRC_DIR}/math/linalg.c
    ${SRC_DIR}/estimation/imu_geom.c
    ${SRC_DIR}/estimation/meas_model.c
    ${SRC_DIR}/estimation/ekf.c
)

add_hg_test(test_ekf ${EKF_SRCS})
add_hg_test(test_sim_convergence ${EKF_SRCS} ${SIM_DIR}/robot_sim.c ${SIM_DIR}/imu_synth.c)
add_hg_test(test_drift ${SRC_DIR}/control/drift.c)
add_hg_test(test_accel_cal ${EKF_SRCS} ${SRC_DIR}/estimation/accel_cal.c)

# Safety logic: arming interlock, battery halt/warn decisions, RC link health.
# arming.h and battery_monitor.h are header-only.
add_hg_test(test_arming)
add_hg_test(test_battery_monitor)
add_hg_test(test_rc_health ${SRC_DIR}/safety/rc_health.c)

# Closed-loop digital-twin scenarios: plant + the real app_ estimator and
# controller, run headless with assertions on emergent behaviour.
# These tests exercise the IMU+EKF path, so define SENSOR_SOURCE_IMU_EKF.
add_hg_test(test_scenarios
    ${EKF_SRCS}
    ${SIM_DIR}/plant.c
    ${SIM_DIR}/imu_synth.c
    ${SRC_DIR}/estimation/imu_convert.c
    ${SRC_DIR}/estimation/accel_cal.c
    ${SRC_DIR}/control/drift.c
    ${SRC_DIR}/control/pid.c
    ${SRC_DIR}/app/control_loop.c
)
target_compile_definitions(test_scenarios PRIVATE SENSOR_SOURCE_IMU_EKF)

# IMU driver: the real latch and SPI driver built against fake_pico/, a
# host stand-in for the pico-sdk calls they use that feeds a model of the
# chip-select latch and the three sensors.
add_hg_test(test_imu_spi
    ${SRC_DIR}/imu/latch.c
    ${SRC_DIR}/imu/imu_spi.c
    ${CMAKE_CURRENT_SOURCE_DIR}/fake_pico/fake_pico.c
)
target_include_directories(test_imu_spi PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/fake_pico
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

# Raw counts -> SI measurement vector: scale factors and per-chip axis map.
add_hg_test(test_imu_convert
    ${SRC_DIR}/math/linalg.c
    ${SRC_DIR}/estimation/imu_geom.c
    ${SRC_DIR}/estimation/meas_model.c
    ${SRC_DIR}/estimation/imu_convert.c
)
