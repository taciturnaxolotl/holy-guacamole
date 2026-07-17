cmake_minimum_required(VERSION 3.13)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(${CMAKE_CURRENT_SOURCE_DIR}/../pico_sdk_import.cmake)

project(motortest C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(motortest
    main.c
    ../src/dshot/dshot.c
    ../src/crsf/crsf.c
)

pico_generate_pio_header(motortest
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/dshot/dshot_bidir_600.pio)

target_include_directories(motortest PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../include   # hw_pins.h
    ${CMAKE_CURRENT_SOURCE_DIR}/../src       # dshot/, crsf/
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/dshot
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/crsf
)

target_link_libraries(motortest PRIVATE
    pico_stdlib
    hardware_pio
    hardware_uart
)

pico_add_extra_outputs(motortest)

# Console + keyboard over USB CDC. Supports picotool -f to exit.
pico_enable_stdio_usb(motortest 1)
pico_enable_stdio_uart(motortest 0)
