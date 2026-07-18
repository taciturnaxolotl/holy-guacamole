cmake_minimum_required(VERSION 3.13)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(${CMAKE_CURRENT_SOURCE_DIR}/../pico_sdk_import.cmake)

project(chanmon C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(chanmon
    main.c
    ../src/crsf/crsf.c
)

target_include_directories(chanmon PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../include   # hw_pins.h
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/crsf  # crsf.h
)

target_link_libraries(chanmon PRIVATE
    pico_stdlib
    hardware_uart
)

pico_add_extra_outputs(chanmon)

# Console over USB CDC. Supports picotool -f to exit.
pico_enable_stdio_usb(chanmon 1)
pico_enable_stdio_uart(chanmon 0)
