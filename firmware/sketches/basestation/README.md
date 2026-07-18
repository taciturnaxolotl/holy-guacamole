# Basestation RF Beacon (Arduino)

A stationary ESP-NOW transmitter for the meltybrain RSSI heading system. It
does one thing: broadcast packets as fast as the radio allows so the spinning
robot can measure their RSSI and derive heading from the phase.

## What it is (and isn't)

- **Is:** a dumb beacon. WiFi + antenna + power, nothing else.
- **Isn't:** it does **not** read RSSI, does **not** connect to an ELRS
  receiver, and has **no** UART. All RSSI measurement and heading math happen
  on the robot (`esp-rssi/`).

## Hardware

- **Board:** Seeed XIAO ESP32-C6
- Just needs power and its antenna. No other wiring.
- The onboard user LED (GPIO15) heartbeats ~1 Hz while running, so a blinking
  LED means the basestation is powered and beaconing.
- Just needs power and its antenna. No other wiring.

## Protocol

ESP-NOW broadcast on channel 1, no encryption, no ACK:

- Payload: `magic` byte (`0xB6`) + rolling `uint32` sequence counter
- The payload content is irrelevant to the heading math — that only uses the
  **received RSSI**. The sequence number is purely for drop detection.

Channel and magic byte must match the robot receiver in `esp-rssi/`.

## Flashing (Arduino IDE)

1. Install the **ESP32 boards package** (Boards Manager → "esp32" by
   Espressif). Any recent version works for the beacon.
2. Open `basestation.ino`.
3. Select board **ESP32C3 Dev Module** (or "XIAO_ESP32C3").
4. Select the serial port, then Upload.

Or with `arduino-cli` (from this sketch folder):

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c3 .
arduino-cli upload  --fqbn esp32:esp32:esp32c3 -p <PORT> .
```

## Where it sits in the system

```
[ basestation ] --ESP-NOW broadcast--> [ robot ESP32-C3 (esp-rssi) ]
   (this repo)                              measures RSSI per packet,
                                            runs heading pipeline,
                                            sends stats to RP2350 over UART
```

The ELRS control link is entirely separate and lives on the RP2350 — the
basestation has nothing to do with it. See `docs/firmware.md` for the full
system layout.
