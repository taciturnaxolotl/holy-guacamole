#include "dshot.h"
#include "dshot_bidir_600.pio.h"

#include "hardware/pio.h"
#include "hardware/clocks.h"
#include "pico/stdlib.h"

/* Shared PIO program offset. Loaded once via dshot_load_program. */
static uint shared_pio_offset;
static bool program_loaded = false;

/* ---- Encoder ---- */

uint32_t dshot_encode(uint16_t command) {
    /* DSHOT frame: 11-bit value + 4-bit CRC + 1 telemetry request bit = 16 bits
     * Telemetry request bit is always set for bidirectional mode. */
    uint16_t packet = (command << 1) | 1;  /* telemetry bit = 1 */

    /* CRC: ~(value ^ (value >> 4) ^ (value >> 8)) & 0x0F */
    uint8_t crc = (~(packet ^ (packet >> 4) ^ (packet >> 8))) & 0x0F;
    packet = (packet << 4) | crc;

    return (uint32_t)packet;
}

/* ---- Decoder ---- */

static const uint8_t gcr_bitlengths[] = {
    0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5, 5
};

static const uint32_t gcr_set_bits[] = {
    0b00000, 0b00001, 0b00011, 0b00111, 0b01111, 0b11111
};

static uint8_t decode_gcr_nibble(uint8_t gcr) {
    switch (gcr) {
        case 0x19: return 0x0;
        case 0x1B: return 0x1;
        case 0x12: return 0x2;
        case 0x13: return 0x3;
        case 0x1D: return 0x4;
        case 0x15: return 0x5;
        case 0x16: return 0x6;
        case 0x17: return 0x7;
        case 0x1A: return 0x8;
        case 0x09: return 0x9;
        case 0x0A: return 0xA;
        case 0x0B: return 0xB;
        case 0x1E: return 0xC;
        case 0x0D: return 0xD;
        case 0x0E: return 0xE;
        case 0x0F: return 0xF;
        default:   return 0xFF;
    }
}

bool dshot_decode_telemetry(uint64_t raw, dshot_telemetry_t *tel) {
    tel->reads++;

    /* Telemetry must start with a 0 bit */
    if (raw & 0x8000000000000000ULL) {
        tel->errors++;
        return false;
    }

    /* Run-length decode GCR from raw sampled bits */
    uint32_t gcr_result = 0;
    int consecutive = 1;
    int current = 0;
    int bits_found = 0;

    for (uint64_t mask = 0x4000000000000000ULL; mask; mask >>= 1) {
        int bit = (raw & mask) != 0;
        if (bit != current) {
            int len = gcr_bitlengths[consecutive];
            gcr_result <<= len;
            if (current) gcr_result |= gcr_set_bits[len];
            bits_found += len;
            current = !current;
            consecutive = 1;
        } else {
            consecutive++;
            if (consecutive > 16) {
                tel->errors++;
                return false;
            }
        }
    }

    /* Account for trailing run */
    int len = gcr_bitlengths[consecutive];
    gcr_result <<= len;
    if (current) gcr_result |= gcr_set_bits[len];
    bits_found += len;

    if (bits_found < 21) {
        tel->errors++;
        return false;
    }

    /* Trim to 21 MSB */
    gcr_result >>= (bits_found - 21);

    /* Convert edge-transition GCR to binary GCR */
    gcr_result ^= (gcr_result >> 1);

    /* Decode four 5-bit GCR nibbles into 16-bit result */
    uint16_t result = 0;
    for (int i = 0; i < 4; i++) {
        uint8_t quintet = (gcr_result >> (15 - i * 5)) & 0x1F;
        uint8_t nibble = decode_gcr_nibble(quintet);
        if (nibble == 0xFF) {
            tel->errors++;
            return false;
        }
        result = (result << 4) | nibble;
    }

    /* Verify CRC (lower 4 bits) */
    uint8_t recv_crc = result & 0x0F;
    result >>= 4;
    uint8_t calc_crc = (~(result ^ (result >> 4) ^ (result >> 8))) & 0x0F;
    if (recv_crc != calc_crc) {
        tel->errors++;
        return false;
    }

    /* Parse eRPM or extended telemetry */
    if (result & 0x100) {
        /* eRPM period */
        uint32_t period_base = result & 0x1FF;
        uint32_t shift = (result >> 9) & 0x07;
        tel->erpm_period_us = period_base << shift;
        if (tel->erpm_period_us > 0) {
            tel->rpm = 60000000UL / (tel->erpm_period_us * MOTOR_POLE_PAIRS);
        }
    } else {
        /* Extended telemetry */
        uint8_t type = (result >> 8) & 0xFF;
        uint8_t value = result & 0xFF;
        switch (type) {
            case DSHOT_EXT_TELE_TEMP:
                tel->temperature_c = value;
                break;
            case DSHOT_EXT_TELE_VOLTAGE:
                tel->voltage_cv = (uint16_t)value * 25;
                break;
            case DSHOT_EXT_TELE_CURRENT:
                tel->current_a = value;
                break;
        }
    }

    return true;
}

/* ---- ESC driver ---- */

bool dshot_load_program(PIO pio) {
    if (program_loaded) return true;

    if (!pio_can_add_program(pio, &dshot_bidir_600_program)) {
        return false;
    }
    shared_pio_offset = pio_add_program(pio, &dshot_bidir_600_program);
    program_loaded = true;
    return true;
}

bool dshot_init(dshot_esc_t *esc, PIO pio, uint gpio) {
    esc->pio = pio;
    esc->gpio = gpio;
    esc->initialized = false;

    if (!program_loaded) return false;

    int sm = pio_claim_unused_sm(pio, false);
    if (sm < 0) return false;
    esc->sm = (uint)sm;

    dshot_bidir_600_program_init(pio, esc->sm, shared_pio_offset, gpio);
    pio_sm_set_enabled(pio, esc->sm, true);

    esc->initialized = true;
    return true;
}

void dshot_send(dshot_esc_t *esc, uint16_t command) {
    if (!esc->initialized) return;
    uint32_t frame = dshot_encode(command);
    pio_sm_put(esc->pio, esc->sm, frame);
}

void dshot_set_throttle(dshot_esc_t *esc, float throttle) {
    if (throttle <= 0.0f) {
        dshot_send(esc, DSHOT_STOP);
        return;
    }
    if (throttle > 1.0f) throttle = 1.0f;
    uint16_t cmd = DSHOT_MIN_THROTTLE +
                   (uint16_t)(throttle * (DSHOT_MAX_THROTTLE - DSHOT_MIN_THROTTLE));
    dshot_send(esc, cmd);
}

void dshot_stop(dshot_esc_t *esc) {
    dshot_send(esc, DSHOT_STOP);
}

bool dshot_read_telemetry(dshot_esc_t *esc) {
    if (!esc->initialized) return false;

    /* Check if both 32-bit halves of telemetry are available in RX FIFO */
    if (pio_sm_get_rx_fifo_level(esc->pio, esc->sm) < 2) return false;

    uint32_t hi = pio_sm_get(esc->pio, esc->sm);
    uint32_t lo = pio_sm_get(esc->pio, esc->sm);
    uint64_t raw = ((uint64_t)hi << 32) | lo;

    return dshot_decode_telemetry(raw, &esc->telemetry);
}
