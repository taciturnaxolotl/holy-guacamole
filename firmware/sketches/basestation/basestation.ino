/*
 * Basestation RF beacon (Arduino / XIAO ESP32-C6).
 *
 * The basestation is a dumb, stationary transmitter. Its only job is to
 * blast ESP-NOW broadcast packets as fast as the radio allows. It does not
 * read RSSI, does not talk to an ELRS receiver, and has no UART peripherals.
 *
 * The robot's onboard ESP32-C3 (esp-rssi) receives these broadcasts and
 * measures the RSSI of each packet. Because the robot spins, that RSSI rises
 * and falls once per revolution, and the robot derives its heading from the
 * phase of that signal. None of that happens here.
 *
 * The onboard user LED heartbeats (~1 Hz) while beaconing, so you can tell at
 * a glance that the basestation is powered and running.
 *
 * Board: Seeed XIAO ESP32-C6. Antenna + power only.
 * Requires the ESP32 Arduino core (any recent version).
 *
 * Protocol: ESP-NOW broadcast on a fixed channel, no encryption, no ACK.
 * Payload = {magic=0xB6, uint32 seq}. The payload is irrelevant to the
 * heading math (that only uses received RSSI); seq is for drop diagnostics.
 * Channel and magic must match esp-rssi.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define ESPNOW_CHANNEL  1
#define BEACON_MAGIC    0xB6

// XIAO ESP32-C6 user LED: GPIO15, active-low (LOW = on).
#define LED_PIN         LED_BUILTIN
#define LED_ON          LOW
#define LED_OFF         HIGH

static const uint8_t broadcast_mac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

typedef struct __attribute__((packed)) {
  uint8_t  magic;   // BEACON_MAGIC, lets the robot filter foreign traffic
  uint32_t seq;     // rolling counter for drop detection / diagnostics
} beacon_pkt_t;

static beacon_pkt_t pkt = { BEACON_MAGIC, 0 };

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_ON);   // solid during bring-up
  delay(100);
  Serial.println("Basestation RF beacon starting");

  // STA mode, no AP association; lock the channel and kill power save so
  // packets go out back-to-back and the robot sees consistent RSSI.
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_ps(WIFI_PS_NONE);
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed; rebooting");
    delay(1000);
    ESP.restart();
  }

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, broadcast_mac, sizeof(broadcast_mac));
  peer.channel = ESPNOW_CHANNEL;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("ESP-NOW add_peer failed; rebooting");
    delay(1000);
    ESP.restart();
  }

  Serial.printf("Ready - broadcasting beacon on channel %d\n", ESPNOW_CHANNEL);
}

void loop() {
  // Fire as fast as the TX queue drains. When it's full esp_now_send returns
  // an error; back off a hair and retry. This paces us to the link rate
  // without needing a send-complete callback (whose signature has churned
  // across ESP32 core versions).
  esp_err_t ret = esp_now_send(broadcast_mac, (uint8_t *)&pkt, sizeof(pkt));
  if (ret == ESP_OK) {
    pkt.seq++;
  } else {
    delayMicroseconds(200);
  }

  // Heartbeat: toggle the LED ~1 Hz so "blinking" means alive and beaconing.
  static uint32_t last_blink = 0;
  static bool lit = true;
  uint32_t now = millis();
  if (now - last_blink >= 500) {
    last_blink = now;
    lit = !lit;
    digitalWrite(LED_PIN, lit ? LED_ON : LED_OFF);
  }
}
