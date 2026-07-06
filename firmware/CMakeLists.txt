cmake_minimum_required(VERSION 3.13)

# Export compile_commands.json so clangd resolves SDK headers.
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(pico_sdk_import.cmake)

project(holy_guacamole C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(holy_guacamole
    src/main.c
    src/dshot/dshot.c
    src/imu/latch.c
    src/imu/imu_spi.c
    src/crsf/crsf.c
)

# Generate PIO header from .pio file
pico_generate_pio_header(holy_guacamole ${CMAKE_CURRENT_SOURCE_DIR}/src/dshot/dshot_bidir_600.pio)

target_include_directories(holy_guacamole PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(holy_guacamole PRIVATE
    pico_stdlib
    pico_multicore
    hardware_pio
    hardware_spi
    hardware_adc
    hardware_uart
    hardware_dma
    hardware_irq
)

pico_add_extra_outputs(holy_guacamole)

# Console over USB CDC, not UART: UART0 is dedicated to the CRSF receiver.
pico_enable_stdio_usb(holy_guacamole 1)
pico_enable_stdio_uart(holy_guacamole 0)
