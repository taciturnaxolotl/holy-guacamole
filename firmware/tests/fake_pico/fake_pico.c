#include "fake_pico.h"

#include "hardware/spi.h"
#include "pico/stdlib.h"
#include "hw_pins.h"

#include <string.h>

/* Register addresses the model needs to know to behave like the parts. */
#define REG_WHO_AM_I        0x0F
#define LSM6_CTRL2          0x11
#define LSM6_CTRL3          0x12
#define LSM6_CTRL3_IF_INC   0x04
#define LSM6_CTRL6          0x15
#define H3LIS_CTRL_REG1     0x20

/* How long a released CS line is still read as low by its sensor. The
 * real figure is the 10k pull-up times the net capacitance (a few
 * hundred ns); this is deliberately on the long side. */
#define CS_RISE_NS 500

#define WRITE_LOG_MAX 256

typedef struct {
    bool is_out;
    bool out_level;
    bool pull;
} pin_t;

typedef struct {
    uint8_t  reg[FAKE_REG_COUNT];
    bool     present;
    uint64_t boot_ns;
    bool     cs_low;
    bool     got_cmd;
    bool     reading;
    bool     ms_bit;        /* H3LIS: auto-increment requested in the command */
    uint8_t  addr;
    bool     released;      /* CS has risen at least once */
    uint64_t released_ns;
    unsigned cs_cycles;
    unsigned bytes;
} slave_t;

struct spi_inst {
    unsigned baud;
    unsigned data_bits;
    spi_cpol_t cpol;
    spi_cpha_t cpha;
    spi_order_t order;
};

static struct spi_inst spi_state;
spi_inst_t *const fake_spi0 = &spi_state;

static pin_t   pin_oe_n;
static pin_t   pin_lat;
static bool    lat_seen;        /* last sampled RCLK level, for edge detect */
static uint8_t shift_reg;
static uint8_t storage_reg;
static slave_t slaves[FAKE_IMU_COUNT];
static uint64_t now_ns;

static fake_write_t write_log[WRITE_LOG_MAX];
static unsigned write_count;
static unsigned contention;
static unsigned cs_glitches;
static unsigned fs_g_live_changes;

static bool level(const pin_t *p) {
    return p->is_out ? p->out_level : p->pull;
}

static bool is_lsm6(int chip) {
    return chip == FAKE_IMU_A;
}

static bool slave_awake(const slave_t *s) {
    return s->present && now_ns >= s->boot_ns;
}

/* Re-evaluate everything that hangs off the two control GPIOs. */
static void board_update(void) {
    bool lat = level(&pin_lat);
    if (lat && !lat_seen) storage_reg = shift_reg;   /* RCLK rising edge */
    lat_seen = lat;

    uint8_t pins = fake_latch_pins();
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        slave_t *s = &slaves[i];
        bool low = !((pins >> i) & 1);
        if (low && !s->cs_low) {
            s->got_cmd = false;
            s->cs_cycles++;
        } else if (!low && s->cs_low) {
            s->released = true;
            s->released_ns = now_ns;
        }
        s->cs_low = low;
    }
}

static bool read_only(int chip, uint8_t addr) {
    if (addr == REG_WHO_AM_I) return true;
    /* Status and output blocks: 1Bh..4Ch on the LSM6, 27h..2Dh on the H3LIS. */
    if (is_lsm6(chip)) return addr >= 0x1B && addr <= 0x4C;
    return addr >= 0x27 && addr <= 0x2D;
}

static void slave_advance(int chip, slave_t *s) {
    if (is_lsm6(chip)) {
        if (s->reg[LSM6_CTRL3] & LSM6_CTRL3_IF_INC) s->addr = (s->addr + 1) & 0x7F;
    } else if (s->ms_bit) {
        s->addr = (s->addr + 1) & 0x3F;
    }
}

/* One byte clocked into a selected sensor; returns what it drives on MISO
 * (0xFF where it leaves the line alone). */
static uint8_t slave_byte(int chip, uint8_t mosi) {
    slave_t *s = &slaves[chip];
    if (!slave_awake(s)) return 0xFF;
    s->bytes++;

    if (!s->got_cmd) {
        /* The only byte ever decoded as R/W + address. */
        s->got_cmd = true;
        s->reading = (mosi & 0x80) != 0;
        if (is_lsm6(chip)) {
            s->addr = mosi & 0x7F;
        } else {
            s->ms_bit = (mosi & 0x40) != 0;
            s->addr = mosi & 0x3F;
        }
        return 0xFF;
    }

    uint8_t out = 0xFF;
    if (s->reading) {
        out = s->reg[s->addr];
    } else if (!read_only(chip, s->addr)) {
        if (is_lsm6(chip) && s->addr == LSM6_CTRL6 &&
            (s->reg[LSM6_CTRL2] & 0x0F) != 0 &&
            (mosi & 0x07) != (s->reg[LSM6_CTRL6] & 0x07)) {
            fs_g_live_changes++;
        }
        s->reg[s->addr] = mosi;
        if (write_count < WRITE_LOG_MAX) {
            write_log[write_count] = (fake_write_t){ (uint8_t)chip, s->addr, mosi };
        }
        write_count++;
    }
    slave_advance(chip, s);
    return out;
}

static uint8_t clock_byte(uint8_t mosi) {
    int selected = 0;
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        const slave_t *s = &slaves[i];
        if (s->cs_low) selected++;
        else if (s->released && now_ns - s->released_ns < CS_RISE_NS) cs_glitches++;
    }
    if (selected > 1) contention++;

    /* SER = MOSI, SRCLK = SCK: the latch shifts on every clock, whoever
     * the byte is meant for. SER enters at QA (bit 0), older bits move
     * toward QH (bit 7). */
    for (int b = 7; b >= 0; b--) {
        int bit = spi_state.order == SPI_MSB_FIRST ? b : 7 - b;
        shift_reg = (uint8_t)((shift_reg << 1) | ((mosi >> bit) & 1));
    }

    uint8_t miso = 0xFF;
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        if (slaves[i].cs_low) miso &= slave_byte(i, mosi);
    }

    unsigned baud = spi_state.baud ? spi_state.baud : 10000000u;
    now_ns += 8ull * 1000000000ull / baud;
    return miso;
}

/* ---- test-side API ---- */

void fake_pico_reset(void) {
    memset(&spi_state, 0, sizeof(spi_state));
    spi_state.order = SPI_MSB_FIRST;   /* the only order the PL022 has */
    memset(slaves, 0, sizeof(slaves));

    /* Board pulls: /OE high (R on GPIO28), RCLK low (R on GPIO5). */
    pin_oe_n = (pin_t){ .pull = true };
    pin_lat  = (pin_t){ .pull = false };
    lat_seen = false;
    shift_reg = 0;
    storage_reg = 0;
    now_ns = 0;

    for (int i = 0; i < FAKE_IMU_COUNT; i++) slaves[i].present = true;

    /* Power-on register defaults (ST DS14623 table 26, DS9012 table 14). */
    uint8_t *a = slaves[FAKE_IMU_A].reg;
    a[REG_WHO_AM_I] = 0x73;
    a[LSM6_CTRL3] = 0x44;
    a[LSM6_CTRL6] = 0x08;
    for (int i = FAKE_IMU_B; i <= FAKE_IMU_C; i++) {
        slaves[i].reg[REG_WHO_AM_I] = 0x32;
        slaves[i].reg[H3LIS_CTRL_REG1] = 0x07;
    }

    write_count = 0;
    contention = 0;
    cs_glitches = 0;
    fs_g_live_changes = 0;
}

uint8_t *fake_imu_regs(int chip) { return slaves[chip].reg; }

void fake_imu_set_present(int chip, bool present) { slaves[chip].present = present; }

void fake_imu_set_boot_ns(int chip, uint64_t ready_at_ns) { slaves[chip].boot_ns = ready_at_ns; }

uint8_t fake_latch_pins(void) {
    return level(&pin_oe_n) ? 0xFF : storage_reg;
}

bool fake_latch_enabled(void) { return !level(&pin_oe_n); }

uint8_t fake_latch_storage(void) { return storage_reg; }

uint64_t fake_time_ns(void) { return now_ns; }

unsigned fake_imu_cs_cycles(int chip) { return slaves[chip].cs_cycles; }

unsigned fake_imu_bytes(int chip) { return slaves[chip].bytes; }

void fake_clear_counters(void) {
    for (int i = 0; i < FAKE_IMU_COUNT; i++) {
        slaves[i].cs_cycles = 0;
        slaves[i].bytes = 0;
    }
    write_count = 0;
}

unsigned fake_write_log(const fake_write_t **log) {
    if (log) *log = write_log;
    return write_count < WRITE_LOG_MAX ? write_count : WRITE_LOG_MAX;
}

unsigned fake_contention_count(void) { return contention; }

unsigned fake_cs_glitch_count(void) { return cs_glitches; }

unsigned fake_fs_g_live_change_count(void) { return fs_g_live_changes; }

unsigned fake_spi_baudrate(void) { return spi_state.baud; }

bool fake_spi_is_mode0_msb_first(void) {
    return spi_state.data_bits == 8 && spi_state.cpol == SPI_CPOL_0 &&
           spi_state.cpha == SPI_CPHA_0 && spi_state.order == SPI_MSB_FIRST;
}

/* ---- pico-sdk calls ---- */

unsigned int spi_init(spi_inst_t *spi, unsigned int baudrate) {
    spi->baud = baudrate;
    /* Same defaults the SDK applies. */
    spi_set_format(spi, 8, SPI_CPOL_0, SPI_CPHA_0, SPI_MSB_FIRST);
    return baudrate;
}

void spi_set_format(spi_inst_t *spi, unsigned int data_bits, spi_cpol_t cpol,
                    spi_cpha_t cpha, spi_order_t order) {
    spi->data_bits = data_bits;
    spi->cpol = cpol;
    spi->cpha = cpha;
    spi->order = order;
}

int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len) {
    (void)spi;
    for (size_t i = 0; i < len; i++) clock_byte(src[i]);
    return (int)len;
}

int spi_read_blocking(spi_inst_t *spi, uint8_t repeated_tx_data, uint8_t *dst,
                      size_t len) {
    (void)spi;
    for (size_t i = 0; i < len; i++) dst[i] = clock_byte(repeated_tx_data);
    return (int)len;
}

static pin_t *pin_for(unsigned int gpio) {
    if (gpio == PIN_SEL_OE_N) return &pin_oe_n;
    if (gpio == PIN_SEL_LAT) return &pin_lat;
    return NULL;
}

/* As on the real SDK: back to an input with the output latch cleared. */
void gpio_init(unsigned int gpio) {
    pin_t *p = pin_for(gpio);
    if (!p) return;
    p->is_out = false;
    p->out_level = false;
    board_update();
}

void gpio_set_dir(unsigned int gpio, bool out) {
    pin_t *p = pin_for(gpio);
    if (!p) return;
    p->is_out = out;
    board_update();
}

void gpio_put(unsigned int gpio, bool value) {
    pin_t *p = pin_for(gpio);
    if (!p) return;
    p->out_level = value;
    board_update();
}

void gpio_set_function(unsigned int gpio, gpio_function_t fn) {
    (void)gpio;
    (void)fn;
}

void busy_wait_us_32(uint32_t delay_us) { now_ns += (uint64_t)delay_us * 1000u; }

void sleep_us(uint64_t us) { now_ns += us * 1000u; }

void sleep_ms(uint32_t ms) { now_ns += (uint64_t)ms * 1000000u; }
