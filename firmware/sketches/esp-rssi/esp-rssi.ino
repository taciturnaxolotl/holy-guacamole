/*
 * ESP32-C3 RSSI heading estimator (Arduino).
 *
 * Onboard the spinning robot. Receives beacon packets via ESP-NOW broadcast
 * from the stationary basestation and measures the RSSI of each received
 * packet. As the robot spins, that RSSI rises and falls once per revolution
 * (antenna pattern / body shadowing), so its phase gives heading. The RSSI
 * comes from the radio's measurement of the received packet
 * (recv_info->rx_ctrl->rssi), NOT from the payload.
 *
 * Runs autocorrelation + PLL heading estimation and streams results over
 * UART (Serial1) to the RP2350 flight controller.
 *
 * REQUIRES ESP32 Arduino core 3.0+  — the receive callback needs the
 * esp_now_recv_info_t signature to expose rx_ctrl->rssi. Core 2.x only
 * hands you the MAC + payload, with no way to read per-packet RSSI.
 *
 * UART protocol (binary, little-endian), ~100 Hz:
 *   [0x55 0xAA] header (2 bytes)
 *   [theta_f32] heading in radians [0, 2pi)  (4 bytes)
 *   [omega_f32] rotation rate in rad/s        (4 bytes)
 *   [locked_u8] 1 if PLL locked, else 0       (1 byte)
 *   [rssi_i8]   latest raw RSSI (dBm)          (1 byte)
 *   Total: 12 bytes per frame.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_timer.h>

extern "C" {
#include "rssi_heading.h"
}

// UART to RP2350.
#define UART_TX_PIN   4    // -> RP2350 GPIO23/SWDIO
#define UART_RX_PIN   5    // <- RP2350 GPIO24/SWDCK
#define UART_BAUD     115200

// ESP-NOW config. Must match the basestation beacon.
#define ESPNOW_CHANNEL  1
#define BEACON_MAGIC    0xB6

// Beacon payload, must match basestation.ino exactly.
typedef struct __attribute__((packed)) {
  uint8_t  magic;   // BEACON_MAGIC
  uint32_t seq;     // rolling counter for drop detection
} beacon_pkt_t;

// Ring buffer for incoming RSSI samples (filled in the WiFi rx callback,
// drained in loop()).
#define RSSI_RING_SIZE 512
typedef struct {
  int8_t  rssi;
  int64_t ts_us;
} rssi_sample_t;

static rssi_sample_t rssi_ring[RSSI_RING_SIZE];
static volatile uint32_t ring_head = 0;
static volatile uint32_t ring_tail = 0;
static volatile uint32_t dropped_beacons = 0;

// UART frame packing.
typedef struct __attribute__((packed)) {
  uint8_t header[2];  // 0x55, 0xAA
  float   theta;
  float   omega;
  uint8_t locked;
  int8_t  rssi;
} uart_frame_t;

static rssi_heading_t rh;

static void on_recv(const esp_now_recv_info_t *recv_info,
                    const uint8_t *data, int len) {
  // Only accept our beacon; ignore any other ESP-NOW / WiFi traffic.
  if (len < (int)sizeof(beacon_pkt_t)) return;
  const beacon_pkt_t *pkt = (const beacon_pkt_t *)data;
  if (pkt->magic != BEACON_MAGIC) return;

  // The heading signal IS the received signal strength of this packet,
  // measured by the radio - not anything in the payload.
  int8_t rssi = recv_info->rx_ctrl->rssi;
  int64_t ts = esp_timer_get_time();

  // Track dropped beacons for diagnostics. Only count forward gaps so a
  // basestation reboot (seq resets to 0) doesn't explode the counter.
  static uint32_t last_seq = 0;
  static bool have_last = false;
  if (have_last && pkt->seq > last_seq + 1) {
    dropped_beacons += (pkt->seq - last_seq - 1);
  }
  last_seq = pkt->seq;
  have_last = true;

  uint32_t next = (ring_head + 1) % RSSI_RING_SIZE;
  if (next == ring_tail) {
    // Buffer full - drop oldest.
    ring_tail = (ring_tail + 1) % RSSI_RING_SIZE;
  }
  rssi_ring[ring_head].rssi = rssi;
  rssi_ring[ring_head].ts_us = ts;
  ring_head = next;
}

void setup() {
  Serial.begin(115200);
  Serial1.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
  delay(100);
  Serial.println("ESP32-C3 RSSI heading receiver starting");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_ps(WIFI_PS_NONE);
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed; rebooting");
    delay(1000);
    ESP.restart();
  }
  esp_now_register_recv_cb(on_recv);

  rssi_heading_init(&rh);
  // Tune for combat robot RPM range (2000-6000 RPM ~ 33-100 Hz).
  rh.interval_us = 167;          // 6 kHz interpolation
  rh.autocorr_interval = 300;    // run autocorr every 300 samples (~50 ms)
  rh.autocorr_min_lag = 20;      // min period ~3.3 ms
  rh.autocorr_max_lag = 200;     // max period ~33 ms
  rh.trigger_thresh = 3.0f;
  rh.arm_thresh = 1.5f;
  rh.min_gap_frac = 0.3f;
  rh.pll_kp = 0.5f;
  rh.pll_ki = 0.01f;

  Serial.println("Ready - listening for ESP-NOW beacon broadcasts");
}

void loop() {
  static uint32_t last_send_ms = 0;
  static uint32_t last_stat_ms = 0;
  uint32_t now = millis();

  // Drain RSSI ring buffer into the heading estimator.
  while (ring_tail != ring_head) {
    rssi_sample_t s = rssi_ring[ring_tail];
    rssi_heading_push(&rh, s.rssi, s.ts_us);
    ring_tail = (ring_tail + 1) % RSSI_RING_SIZE;
  }

  rssi_estimate_t est = rssi_heading_estimate(&rh);

  // Emit a UART frame at 100 Hz.
  if (now - last_send_ms >= 10) {
    uart_frame_t frame;
    frame.header[0] = 0x55;
    frame.header[1] = 0xAA;
    frame.theta = est.locked ? est.theta : 0.0f;
    frame.omega = est.omega * 6000.0f * 2.0f * 3.14159f;  // samples/s -> rad/s
    frame.locked = est.locked ? 1 : 0;

    // Latest RSSI from the ring (or 0 if empty).
    if (ring_head != ring_tail) {
      uint32_t idx = (ring_head == 0) ? RSSI_RING_SIZE - 1 : ring_head - 1;
      frame.rssi = rssi_ring[idx].rssi;
    } else {
      frame.rssi = 0;
    }

    Serial1.write((uint8_t *)&frame, sizeof(frame));
    last_send_ms = now;
  }

  // 1 Hz diagnostics on the USB serial.
  if (now - last_stat_ms >= 1000) {
    Serial.printf("locked=%d omega=%.1f rad/s dropped=%lu\n",
                  est.locked,
                  (double)(est.omega * 6000.0f * 2.0f * 3.14159f),
                  (unsigned long)dropped_beacons);
    last_stat_ms = now;
  }

  delay(1);  // ~1 kHz loop
}
