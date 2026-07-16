# Native SITL simulator build. Links the EXACT estimation + control
# modules against a hand-rolled 2D rigid-disc plant and a raylib front-end
# so the real firmware logic can be test-driven with no hardware.

cmake_minimum_required(VERSION 3.13)
project(holy_guacamole_sim C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../src)
set(SIM_DIR ${CMAKE_CURRENT_SOURCE_DIR})

find_package(raylib REQUIRED)

add_executable(drive
    ${SIM_DIR}/drive.c
    ${SIM_DIR}/zorro_input.c
    ${SIM_DIR}/plant.c
    ${SIM_DIR}/imu_synth.c
    ${SRC_DIR}/math/linalg.c
    ${SRC_DIR}/estimation/imu_geom.c
    ${SRC_DIR}/estimation/meas_model.c
    ${SRC_DIR}/estimation/ekf.c
    ${SRC_DIR}/estimation/imu_convert.c
    ${SRC_DIR}/estimation/accel_cal.c
    ${SRC_DIR}/control/drift.c
    ${SRC_DIR}/control/pid.c
    ${SRC_DIR}/app/control_loop.c
)

target_include_directories(drive PRIVATE ${SRC_DIR} ${SIM_DIR})
target_compile_definitions(drive PRIVATE SENSOR_SOURCE_IMU_EKF)
if(APPLE)
    target_link_libraries(drive PRIVATE raylib m "-framework IOKit" "-framework CoreFoundation")
else()
    target_link_libraries(drive PRIVATE raylib m)
endif()

# Gamepad test harness (standalone, no firmware deps)
add_executable(pad_test ${SIM_DIR}/pad_test.c)
target_link_libraries(pad_test PRIVATE raylib m)

# Zorro visual mapper (IOKit + raylib)
if(APPLE)
    add_executable(zorro_mapper ${SIM_DIR}/zorro_mapper.c)
    target_link_libraries(zorro_mapper PRIVATE raylib m "-framework IOKit" "-framework CoreFoundation")

    # Automated Zorro HID detector (terminal-only, no raylib)
    add_executable(zorro_detect ${SIM_DIR}/zorro_detect.c)
    target_link_libraries(zorro_detect PRIVATE "-framework IOKit" "-framework CoreFoundation")
endif()
