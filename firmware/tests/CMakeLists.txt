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

set(RSSI_SRCS
    ${SRC_DIR}/estimation/edge_pll.c
    ${SRC_DIR}/estimation/rssi_interp.c
    ${SRC_DIR}/estimation/autocorr.c
    ${SRC_DIR}/estimation/rssi_heading.c
)

add_hg_test(test_rssi_pipeline ${RSSI_SRCS} ${EKF_SRCS})

# Closed-loop digital-twin scenarios: plant + the real app_ estimator and
# controller, run headless with assertions on emergent behaviour.
add_hg_test(test_scenarios
    ${EKF_SRCS}
    ${RSSI_SRCS}
    ${SIM_DIR}/plant.c
    ${SIM_DIR}/imu_synth.c
    ${SRC_DIR}/estimation/imu_convert.c
    ${SRC_DIR}/estimation/accel_cal.c
    ${SRC_DIR}/control/drift.c
    ${SRC_DIR}/control/pid.c
    ${SRC_DIR}/app/control_loop.c
)
