cmake_minimum_required(VERSION 3.13)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Reuse the parent project's SDK import shim.
include(${CMAKE_CURRENT_SOURCE_DIR}/../pico_sdk_import.cmake)

project(elrs_passthrough C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(elrs_passthrough
    main.c
    usb_descriptors.c
)

target_include_directories(elrs_passthrough PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}                 # tusb_config.h
    ${CMAKE_CURRENT_SOURCE_DIR}/../include      # hw_pins.h
)

target_link_libraries(elrs_passthrough PRIVATE
    pico_stdlib
    hardware_uart
    hardware_gpio
    tinyusb_device
)

pico_add_extra_outputs(elrs_passthrough)

# We drive TinyUSB directly; no pico stdio on USB or UART.
pico_enable_stdio_usb(elrs_passthrough 0)
pico_enable_stdio_uart(elrs_passthrough 0)
