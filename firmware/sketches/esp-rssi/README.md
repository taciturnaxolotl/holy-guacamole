# ESP32-C3 RSSI Heading Receiver (Arduino)

Onboard the spinning robot. Receives beacon packets via ESP-NOW broadcast,
measures the **received signal strength of each packet** (which rises and falls
once per revolution as the robot spins), runs autocorrelation + PLL heading
estimation, and streams results over UART to the RP2350 flight controller.

The heading signal is the radio's measured RSSI of the received packet, not
anything carried in the payload.

## Requirements

- **ESP32 Arduino core 3.0 or newer.** The receive callback needs the
  `esp_now_recv_info_t` signature to read per-packet RSSI (`rx_ctrl->rssi`).
  Core 2.x only exposes the MAC + payload and cannot read RSSI here.

## Hardware

- **Board:** ESP32-C3 (Seeed XIAO ESP32-C3 or any ESP32-C3)
- **UART TX:** GPIO4 → RP2350 GPIO23/SWDIO
- **UART RX:** GPIO5 ← RP2350 GPIO24/SWDCK
- **Baud rate:** 115200 (Serial1)

## Sketch layout

Arduino compiles every `.c`/`.cpp` in the sketch folder, so the ported RSSI
pipeline lives right alongside the sketch:

```
esp-rssi/
  esp-rssi.ino        # WiFi + ESP-NOW + UART glue
  rssi_heading.c/.h   # pipeline top level: interp + autocorr + edge PLL
  rssi_interp.c/.h    # resample RSSI onto a uniform time grid
  autocorr.c/.h       # rotation-period acquisition
  edge_pll.c/.h       # edge-triggered phase lock
```

## UART protocol

Binary frames at ~100 Hz:

```
[0x55 0xAA] [theta_f32] [omega_f32] [locked_u8] [rssi_i8]
  header      rad [0,2pi)  rad/s       0/1          dBm
```

Total: 12 bytes per frame.

## Flashing (Arduino IDE)

1. Install the **ESP32 boards package** 3.0+ (Boards Manager → "esp32").
2. Open `esp-rssi.ino`.
3. Select board **ESP32C3 Dev Module** (or "XIAO_ESP32C3"), pick the port,
   Upload.

Or with `arduino-cli` (from this sketch folder):

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c3 .
arduino-cli upload  --fqbn esp32:esp32:esp32c3 -p <PORT> .
```

The USB serial prints 1 Hz diagnostics (lock state, omega, dropped beacons);
the heading frames go out on Serial1 to the RP2350.

## Transmitter Side

The stationary basestation (`basestation/`) broadcasts beacon packets on
ESP-NOW channel 1, no encryption. Each packet is a `{magic=0xB6, seq}` struct;
this receiver rejects anything without the magic byte and uses `seq` only to
count dropped packets. Channel and magic byte must match on both ends.
