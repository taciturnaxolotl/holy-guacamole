# Holy Guacamole — Carrier PCB Specification

**Document status:** Draft v1.3c — updated to match current `circuit.py` Rev A schematic: solder-down ELRS receiver `U7`, 3S-ready VBUS, protection diodes documented  
**Robot:** Holy Guacamole — 1lb meltybrain antweight, MRCA full-combat  

---

## Overview

The carrier PCB is a purpose-built board for a Seeed XIAO RP2350 module. It is **not** a bare-RP2350 compute board: the XIAO provides the RP2350, flash, USB, crystal, and onboard 3.3V regulator. The carrier provides power conditioning, sensors, connectors, and robot-specific IO.

Primary carrier jobs:

- Mount the XIAO RP2350 flat as an SMD/castellated module; no XIAO pin headers.
- Generate a local regulated 5V rail from the switched LiPo bus (2S nominal, 3S-ready to 12.6V) using an AP63205 fixed-5V buck regulator.
- Use the XIAO 3.3V rail for IMUs, the SPI-loaded chip-select latch, analog sensing, and control logic; power the solder-down BetaFPV ELRS Lite receiver (`U7`) from the carrier 5V rail per its vendor spec.
- Route SPI to one inner LSM6DSV320X 6-axis/high-G IMU and two outer H3LIS331DL high-G accelerometers.
- Use a SN74HC595PWR SPI-loaded latch for IMU chip-selects and SK9822 LED-output enable; firmware blanks the latch outputs while shifting a new select byte.
- Connect to the Repeat AM32 Dual Brushless Drive ESC using two direct bidirectional DSHOT/EDT lines.
- Keep independent battery voltage sensing on the carrier.
- Rely on AM32 bidirectional DSHOT / EDT for motor eRPM/current/voltage telemetry; no external Kelvin shunt in Rev A.
- Provide a dedicated orange 2-3S TinySLED meltybrain heading output using XIAO edge pin D1/A1 and one MOSFET low-side switch; no underside XIAO GPIOs are used for runtime IO.
- Retain chained top/bottom SK9822 RGB status LEDs for boot/error/mode indication and expose only essential VBAT/SWD/GND test pads. The older piezo input is deferred because D2/A2 is now used by the chip-select latch output-enable.

The PCB mounts near the chassis centre. Final IMU coordinates must be measured from the actual chassis rotation centre and copied into firmware calibration constants.

---

## Current schematic reference designators

These names match the current SKiDL schematic in `circuit.py`.

| Ref | Function |
|---|---|
| `U1` | Seeed XIAO RP2350 SMD module |
| `U2` | AP63205 fixed 5.0V buck regulator |
| `U3` | SN74HC595PWR SPI-loaded chip-select / LED-enable latch |
| `U4` | LSM6DSV320XTR inner 6-axis / high-G IMU |
| `U5`, `U6` | H3LIS331DLTR outer high-G accelerometers |
| `U7` | BetaFPV ELRS Lite receiver, solder-down module footprint |
| `U8`, `U9` | SN74AHCT1G125 3.3V-to-5V SK9822 data/clock buffers |
| `U10`, `U11` | SK9822-EC20 2×2mm addressable status LEDs, top and bottom chained pair |
| `Q1` | AO3402 low-side MOSFET for orange TinySLED heading LED |
| `J1` | Switched 2S/3S LiPo / VBUS carrier power input |
| `J2` | External orange 2-3S TinySLED heading LED connector |
| `J4` | Repeat AM32 dual ESC signal connector |
| `D2` | SMAJ15CA bidirectional TVS across VBUS at power entry |
| `D3`, `D4` | PESD5V0V1BB ESD clamps on DSHOT1/DSHOT2 at J4 |

`J3` piezo and `J5` from the older two-separate-ESC-connector version are retired/deferred in the current edge-pin-only Rev A schematic. The older `J6` receiver fly-lead connector is replaced by the solder-down `U7` receiver footprint.

---

## Physical constraints

| Parameter | Value |
|---|---|
| Board shape | Rectangular with rounded corners |
| Board dimensions | **40mm × 50mm** (width × length) |
| Front direction | 50mm axis is front-to-back; front = top edge in KiCad |
| Max board thickness | 1.0mm preferred; standard 1.6mm may violate chassis Z budget |
| Max component height above board | 2.5mm nominal, set by XIAO module height |
| Mounting | 4× M3 brass heat-set inserts in chassis, M3×6 SHCS from below; holes at four corners inset ~2.5mm from edges |
| Connector exits | J2 heading LED on front (top) edge; J1 power and J4 ESC signal on rear (bottom) edge; all via 26AWG silicone fly-leads on compact non-relief 0.25sqmm SolderWire pads, epoxied after soldering; 16AWG stays in the off-board battery/switch/ESC loop and never lands on the carrier |
| Operating temperature | 0–60°C ambient expectation, with local motor/ESC heating nearby |
| Vibration/impact | Extreme; reinforce heavy/tall components and wire exits with epoxy or strain relief |

### Board coordinate system

KiCad origin at top-left corner of the 40×50mm rectangle. Board center is at (20mm, 25mm). The +Y axis points toward the rear edge; the front/heading edge is at Y=0.

Mounting hole centers (4× M3):

| Hole | X (mm) | Y (mm) |
|---:|---:|---:|
| MH1 | 2.5 | 2.5 |
| MH2 | 37.5 | 2.5 |
| MH3 | 2.5 | 47.5 |
| MH4 | 37.5 | 47.5 |

### IMU placement on rectangular board

The 40×50mm rectangle provides ample clearance for the original IMU radii. All three IMU centroids fit well within the board outline with room for solder mask, routing, and connector pads.

Rev A layout rule:

- Board center at (20, 25) is the rotation reference point.
- Place IMUs at the nominal radii and angles listed below.
- Firmware must use the **measured** post-layout IMU coordinates, not just nominal values from this document.

---

## Module: Seeed XIAO RP2350

**Reference:** `U1`  
**Datasheet / getting started:** https://wiki.seeedstudio.com/xiao_rp2350_getting_started/

| Parameter | Value |
|---|---|
| Dimensions | 21 × 17.5 × 2.5mm |
| Mounting | Castellated SMD pads, soldered flat to carrier; no pin headers |
| Mechanical retention | Small epoxy fillet at four corners after soldering |
| CPU | RP2350, dual Cortex-M33 @ 150MHz, hardware FPU |
| Flash | 4MB W25Q32 onboard; no carrier flash required |
| Crystal | 12MHz onboard; no carrier crystal required |
| 5V input | XIAO `5V/VBUS` pad fed from carrier AP63205 5V rail |
| 3.3V output | XIAO 3.3V rail powers carrier logic/sensors; do not exceed XIAO 3.3V output budget |
| USB-C | Onboard; use for bench programming/config, not combat field wiring |
| SWD | Break out SWDIO/SWDCLK/GND to test pads |

Firmware workload intent:

| Core | Responsibility |
|---|---|
| Core 0 | IMU SPI DMA / sensor fusion / heading EKF / RPM estimation |
| Core 1 | CRSF, DSHOT/EDT, drift control loop, telemetry/status |

---

## Power architecture

Rev A keeps an independent controller buck regulator. The Repeat AM32 dual ESC BEC is **not connected** to the carrier 5V rail.

```text
2S LiPo (3S-ready bus)
  -> Fingertech / main switch
      -> switched battery bus
          -> Repeat AM32 dual ESC power pads
          -> carrier J1 VBUS/GND
              -> D2 SMAJ15CA TVS clamp at power entry
              -> AP63205 fixed 5.0V buck
                  -> 5V rail
                      -> XIAO 5V/VBUS pad
                      -> chained top/bottom SK9822 status LEDs + AHCT buffers
                      -> U7 BetaFPV ELRS Lite receiver 5V pad (solder-down)
                  -> XIAO onboard 3.3V regulator
                      -> LSM6DSV320X + H3LIS331DL IMUs
                      -> SN74HC595 chip-select latch
                      -> analog clamps / control logic
              -> J2 pin 1 TinySLED VBUS feed
                  -> external orange 2-3S TinySLED
                  -> J2 pin 2 HEAD_SW
                  -> Q1 AO3402 low-side switch to GND
```

### ESC BEC policy

The Repeat AM32 Dual ESC includes a 5V BEC, but Rev A leaves it isolated. Do **not** tie the ESC BEC directly to the carrier AP63205 5V rail.

Reasons to keep the carrier buck in Rev A:

- Known 5V source on the controller board.
- Better controller independence if the ESC resets or current-limits hard.
- Avoids importing motor-switching/BEC noise into IMU and analog domains until measured.
- Simpler debugging: battery into `J1` means carrier power is deterministic.

Possible Rev B change:

- Remove/DNP AP63205 buck and use ESC BEC only, **or** add a solder-jumper / ideal-diode power selector.
- Before doing that, confirm ESC BEC current rating, voltage tolerance, startup behavior, and noise under motor load.

### Buck converter: AP63205

**Reference:** `U2`  
**Part:** Diodes Inc. AP63205WU-7, fixed 5.0V, LCSC `C2071056`

| Parameter | Value |
|---|---|
| Package | TSOT-23-6 |
| Input voltage | 3.8–32V part capability; design VBUS is 2S LiPo 6.0–8.4V nominal, 3S-ready to 12.6V |
| Output voltage | Fixed 5.0V; FB pin connects to 5V, no feedback divider |
| Output current | 2A device rating; actual board load is far lower unless external LEDs are overdriven |
| Inductor | 4.7uH, Bourns SRP4020TA-4R7M / LCSC `C2041623` in current schematic |

Required local passives in current schematic:

| Ref | Value | Function |
|---|---|---|
| `C1` | 22uF | VBUS input bulk, rated at least 25V |
| `C2` | 100nF | High-frequency VIN bypass close to U2 VIN/GND |
| `C3` | 100nF | Bootstrap capacitor from BST to SW |
| `C4`, `C5` | 22uF each | 5V output capacitance near L1/U2 return path |
| `C6` | 10uF | 3.3V bulk near sensor/control load cluster |

Power-entry protection in current schematic:

| Ref | Part | Function |
|---|---|---|
| `D2` | SMAJ15CA, LCSC `C110044` | Bidirectional 15V-standoff TVS across VBUS/GND at J1; clamps below the AP63205 32V input rating with margin for 3S |

Layout requirements:

- Place `C1`/`C2` tight to U2 VIN/GND.
- Keep the `SW` copper area compact.
- Keep the buck switch node and inductor away from IMUs, CRSF, VBAT sense, and heading LED control/test nodes.
- Use wide copper for VBUS and 5V where LED pulses can draw peak current.

---

## IMU array: 1× LSM6DSV320X + 2× H3LIS331DL

**References:** `U4`, `U5`, `U6`  
**Parts:** `U4` STMicroelectronics LSM6DSV320XTR, LGA-14, LCSC `C26633007`; `U5`/`U6` STMicroelectronics H3LIS331DLTR, LGA-16L 3×3mm, LCSC `C2655074`

### Placement geometry

All three IMUs share SPI SCK/MOSI/MISO and use independent active-low chip-selects generated by `U3` SN74HC595PWR. The latch is loaded over the same SPI MOSI/SCK nets while its outputs are blanked by `SEL_OE_N`.

Nominal geometry intent:

| Sensor | Nominal angle | Nominal radius | Centroid (mm from board center) | Rationale |
|---|---:|---:|---|---|
| IMU-A | 0° / +X right | 12mm | (+12, 0) → KiCad (32, 25) | Inner LSM6DSV320X reference sensor with gyro and lower G loading |
| IMU-B | 90° / +Y rear | 18mm | (0, +18) → KiCad (20, 43) | Orthogonal outer H3LIS331DL sensor for X/Y decomposition |
| IMU-C | 210° | 18mm | (-15.6, -9) → KiCad (4.4, 16) | Asymmetric outer H3LIS331DL placement breaks heading singularities |

G loading at 4000RPM:

| Radius | Centrifugal G |
|---:|---:|
| 12mm | ~216G |
| 18mm | ~324G |

All IMU centroids are at least 4mm from the nearest board edge on the 40×50mm rectangle, providing comfortable clearance for solder mask, silkscreen, and routing. If the outer radius changes, update the firmware measurement model.

### IMU configuration

| Parameter | IMU-A LSM6DSV320X | IMU-B/IMU-C H3LIS331DL |
|---|---|---|
| Sensor role | Inner 6-axis/high-G reference with gyro | Outer high-G accelerometers |
| Interface | SPI mode 0, shared bus | SPI mode 0, up to 10MHz |
| Output data rate | Firmware-selected high-rate accel/gyro mode | 1000Hz target |
| Axes used | Gyro + X/Y acceleration for heading estimation | X/Y in-plane; Z available but not central to heading model |
| Support pins | SDx and SCx tied to GND; INT/aux pins unused/NC | Reserved pin 10 to GND, pin 15 to Vdd; INT pins unused/NC |

### Decoupling

Current schematic has:

- `C8` and `C11` = 100nF local capacitors for IMU-A LSM6DSV320X `VDD` and `VDDIO`.
- `C9`, `C10` = 100nF local capacitors for IMU-B/IMU-C H3LIS331DL `Vdd`.
- `C6` and `C13` = 10uF 3.3V bulk capacitors for the sensor/control cluster (C13 at the far end of the IMU spread).

ST guidance for these IMUs calls for local 100nF bypassing at each supply pin plus nearby bulk capacitance. In layout, keep `C6` close to the IMU/3.3V/latch cluster and place `C13` near whichever outer IMU (U5/U6) lands farthest from C6, so the radial 3V3 route stays stiff at both ends.

### SPI wiring

| Signal | Source | Notes |
|---|---|---|
| `SPI_SCK` | XIAO D8/GPIO2 | Shared SPI clock |
| `SPI_MOSI` | XIAO D10/GPIO3 | Shared MOSI |
| `SPI_MISO` | XIAO D9/GPIO4 | Shared MISO |
| `CS_A` | SN74HC595 QA / pin 15 | IMU-A active-low chip-select |
| `CS_B` | SN74HC595 QB / pin 1 | IMU-B active-low chip-select |
| `CS_C` | SN74HC595 QC / pin 2 | IMU-C active-low chip-select |

All three IMUs run in 4-wire SPI mode; I2C is not used anywhere on the carrier. With two identical H3LIS331DL parts, I2C would not work anyway: the part exposes only one SA0 address-select level, so both outer sensors would collide on the same bus address. Per-device SPI chip-selects from the SN74HC595 avoid that entirely, and the H3LIS SDO/SA0 pads are used as SPI data outputs, not address straps.

`R6`, `R7`, and `R8` are 33Ω series resistors from each IMU SDO to shared MISO for ringing and bus-contention limiting.

Each CS line has a 10kΩ pull-up (`R3`, `R4`, `R5`) so the IMUs remain deselected while the RP2350 boots or while the SN74HC595 outputs are high-Z/blanked.

### IMU readout timing

Rev A uses one shared `SPI_MISO` net, so firmware must select **only one IMU at a time**. Do not assert `CS_A`, `CS_B`, and `CS_C` simultaneously on this hardware: all selected IMUs would drive the same MISO net through the 33Ω resistors, causing contention and invalid data.

Timing budget at 10MHz SPI:

| Operation | Approximate time |
|---|---:|
| H3LIS331DL X/Y burst read: 1 address byte + 4 data bytes = 40 bits | ~4us per outer IMU |
| Three ideal sequential IMU reads | ~12us |
| SN74HC595 select-byte shift: 8 bits plus `SEL_LAT` pulse | <1us at 10MHz plus firmware overhead |
| Practical three-IMU read set with latch CS management | ~15-30us depending on firmware gaps |
| Angular skew at 4000RPM for 30us | ~0.72deg |

Firmware requirements:

- Maintain a cached 8-bit SN74HC595 latch image. Update it only while `SEL_OE_N` is high so latch outputs are high-Z and the external pull-ups keep all CS/LED-enable nets inactive.
- Keep exactly one IMU CS low during each SPI data transaction.
- Timestamp the read set and, if needed, compensate fixed read skew in the estimator. Expected Rev A skew is below other likely error sources such as IMU placement tolerance and accelerometer nonlinearity.
- Parallel-MISO PIO readout is a Rev B optimization only. It would require routing `MISO_A`, `MISO_B`, and `MISO_C` to separate direct RP2350 GPIOs, while sharing SCK/MOSI/CS timing. It is not supported by the current edge-pin-only Rev A schematic.
- Parallel MISO removes bus readout skew but does not synchronize the IMUs' internal sample clocks; data-ready timing still matters if sample simultaneity becomes a limiting error source.

### Axis orientation convention

Mount each chip so:

- chip X axis points radially outward from the rotation centre;
- chip Y axis points tangentially in the defined positive rotation direction.

Verify against the H3LIS331DL datasheet axis diagram before fabrication. Wrong axis orientation is hard to debug after assembly.

---

## SPI-loaded chip-select latch

**Reference:** `U3`  
**Part:** SN74HC595PWR, LCSC `C273642`

The XIAO edge pads are pin-limited, so the carrier uses a SPI-loaded serial-in/parallel-out latch instead of a SPI GPIO expander. It consumes no dedicated MISO line and uses only the shared `SPI_MOSI`/`SPI_SCK` plus two direct GPIO controls: `SEL_OE_N` and `SEL_LAT`.

| Latch function | Signal |
|---|---|
| Output blanking from XIAO | `SEL_OE_N`, XIAO D2/A2/GPIO42 -> U3 `/OE` |
| Latch clock from XIAO | `SEL_LAT`, XIAO D3/A3/GPIO43 -> U3 `RCLK` |
| Serial data | `SPI_MOSI` -> U3 `SER` |
| Shift clock | `SPI_SCK` -> U3 `SRCLK` |
| IMU-A select | `CS_A` |
| IMU-B select | `CS_B` |
| IMU-C select | `CS_C` |
| SK9822 level-shifter output enable | `LED_OE_N`, from SN74HC595 QD / pin 3 |

Boot-safe pull-ups:

- `R1`: pulls `SEL_OE_N` high so SN74HC595 outputs are high-Z while XIAO boots.
- `R11`: pulls `SEL_LAT` low so startup noise does not latch garbage into the outputs.
- `R2`: pulls `LED_OE_N` high so AHCT LED buffers are disabled while U3 is blanked or uninitialized.
- `R3`/`R4`/`R5`: pull `CS_A`/`CS_B`/`CS_C` high so all IMUs are deselected while U3 outputs are high-Z/blanked.

### Firmware latch protocol

The SN74HC595 has no chip-select input and shares the IMU/status SPI clock and MOSI nets, so firmware must treat latch updates as explicit bus transactions with outputs blanked:

1. Drive `SEL_OE_N` high to put U3 QA-QH high-Z. External pull-ups then force `CS_A`, `CS_B`, `CS_C`, and `LED_OE_N` inactive/high.
2. Shift the desired 8-bit latch image on `SPI_MOSI` using `SPI_SCK`.
3. Pulse `SEL_LAT` high then low to transfer the shifted byte to QA-QH.
4. Drive `SEL_OE_N` low only for the selected IMU or LED update window.
5. Return to a safe all-inactive image and/or drive `SEL_OE_N` high before changing targets.

Latch bit assignment in Rev A:

| SN74HC595 output | Net | Active state | Firmware meaning |
|---|---|---:|---|
| QA / pin 15 | `CS_A` | 0 | Select IMU-A LSM6DSV320X |
| QB / pin 1 | `CS_B` | 0 | Select IMU-B H3LIS331DL |
| QC / pin 2 | `CS_C` | 0 | Select IMU-C H3LIS331DL |
| QD / pin 3 | `LED_OE_N` | 0 | Enable SK9822 AHCT data/clock buffers |
| QE-QH, QH' | NC | — | Leave unused; shift deterministic 1s for inactive outputs |

Firmware safety rules:

- Never enable outputs with more than one of `CS_A`, `CS_B`, or `CS_C` low.
- Keep `LED_OE_N` high during IMU reads and latch changes so normal IMU SPI traffic does not clock garbage into the SK9822.
- Keep all CS lines high while updating the SK9822; only QD/`LED_OE_N` should be low for LED writes.
- Initialize `SEL_OE_N` as a pulled/high GPIO before configuring the SPI peripheral if possible. `R1` provides the hardware fallback during reset.
- Because latch shifting uses the same `SPI_MOSI`/`SPI_SCK` as the IMUs, do not shift a new latch byte while any IMU CS is enabled.

---

## Repeat AM32 dual ESC / DSHOT / EDT

**External ESC:** Repeat AM32 Dual Brushless Drive ESC  
**Carrier connector:** `J4`, one combined signal harness

`J4` pinout:

| Pin | Signal | Notes |
|---:|---|---|
| 1 | GND | ESC signal/battery ground reference |
| 2 | `DSHOT1` | AM32 channel 1 / white signal wire, bidirectional DSHOT + EDT |
| 3 | `DSHOT2` | AM32 channel 2 / yellow signal wire, bidirectional DSHOT + EDT |
| 4 | GND | Second local return / harness strain relief |

XIAO pins:

| Signal | XIAO pin | Series part |
|---|---|---|
| `DS1_IO` -> `DSHOT1` | D4/SDA/GPIO6 | `R12` = 33Ω |
| `DS2_IO` -> `DSHOT2` | D5/SCL/GPIO7 | `R13` = 33Ω |

Requirements:

- Use RP2350 PIO/DMA/timer support; do not bit-bang in a jittery control loop.
- Keep DSHOT lines direct from RP2350-capable GPIOs; do not route through the SN74HC595 latch.
- `D3`/`D4` PESD5V0V1BB bidirectional 5V ESD clamps sit at J4 pins 2/3 to ground, on the connector side of `R12`/`R13`.
- **Firmware must use DSHOT600** for normal bidirectional DSHOT/EDT operation at ~4000–4300RPM. DSHOT300 is allowed only for bench/low-speed testing because the effective bidirectional command/telemetry update rate is marginal near strike RPM.
- Bidirectional DSHOT/EDT returns eRPM and extended telemetry over the same signal wires; no extra telemetry UART is required in Rev A.
- Configure AM32 motor pole count correctly. For a 14-pole outrunner, pole pairs = 7 and mechanical RPM = eRPM / 7. Verify actual motor magnet pole count instead of guessing.
- ESC BEC output is not connected to this carrier in Rev A.

High-current ESC battery and motor phase wiring must not pass through the carrier PCB. The carrier only handles logic-level DSHOT/EDT and its own VBUS feed.

---

## CRSF / ELRS

**Reference:** `U7` — solder-down module footprint (Eyeliner repo landing pattern), no fly-lead connector  
**Receiver:** BetaFPV ELRS Lite Receiver 2.4GHz, Flat Antenna V1.2 variant, https://betafpv.com/products/elrs-lite-receiver

Vendor-listed receiver facts for the selected variant:

| Parameter | Value |
|---|---|
| MCU | ESP8285 |
| Serial output protocol | CRSF |
| Input voltage | 5V |
| Frequency band | 2.4GHz ISM |
| Telemetry RF power | 17mW |
| Size / mass | 11 × 10 × 3mm, 0.46g |
| Antenna | Integrated SMD ceramic antenna |

| U7 pad | Signal | Notes |
|---:|---|---|
| 1 | GND | Receiver ground |
| 2 | 5V | Receiver power from carrier AP63205 5V rail; BetaFPV specifies 5V input |
| 3 | receiver TX/T | Drives carrier `CRSF_RX` -> XIAO D7/GPIO1 |
| 4 | receiver RX/R | Driven by carrier `CRSF_TX` <- XIAO D6/GPIO0 |

CRSF caveat:

- CRSF is normally non-inverted UART at 420000 baud. SBUS is the common inverted-serial trap; Rev A is using CRSF, not SBUS.
- Rev A schematic has no discrete CRSF inverter, which is appropriate for the selected BetaFPV ELRS Lite CRSF output.
- Pad order GND, 5V, TX/T, RX/R is user-confirmed against the Eyeliner landing pattern; re-verify on the physical receiver before soldering and keep the cross-connection: receiver TX -> XIAO RX (`CRSF_RX`), receiver RX <- XIAO TX (`CRSF_TX`).

Receiver placement: soldered directly to the carrier with the antenna end at the board edge nearest the chassis wall; keep the antenna away from copper pours, battery, the buck inductor/switch node, and motor phase wires. Add foam/epoxy support after soldering so impacts do not peel the module pads.

---

## Analog / event inputs

### Battery voltage sense

The carrier keeps an independent battery divider even though the ESC can provide telemetry. This gives pack voltage during bring-up and if ESC telemetry is unavailable.

| Parameter | Value |
|---|---|
| XIAO ADC pin | A0/D0/GPIO40 |
| Net | `VBAT_SNS` |
| Divider high-side | `R9` = 120kΩ from VBUS |
| Divider low-side | `R10` = 33kΩ to GND |
| Filter | `C12` = 100nF to GND |
| ADC voltage at 8.4V pack | ~1.81V |
| ADC voltage at 12.6V 3S full charge | ~2.72V |
| ADC voltage at 6.0V pack | ~1.29V |

Use this for independent low-battery warning and telemetry. Firmware can fuse/compare this with AM32 EDT voltage.

### Current sensing

There is **no INA180 / Kelvin shunt current-sense circuit in Rev A**.

Current/eRPM telemetry path:

- AM32 bidirectional DSHOT provides eRPM feedback per motor.
- AM32 Extended DSHOT Telemetry can provide ESC voltage/current/temperature data when supported/configured.
- ESC current limiting remains local to the ESC.

If future testing shows AM32 current telemetry is insufficient, add an external inline shunt and INA180 in a later revision. Do not route motor current through this carrier PCB.

### Deferred piezo / impact input

The older protected piezo impact input is not populated in the current edge-pin-only Rev A schematic because XIAO D2/A2/GPIO42 is used as `SEL_OE_N` for the SN74HC595 output blanking. Impact classification can be revisited in Rev B using an underside GPIO/ADC pad or a different IO tradeoff.

---

## Status LED: SK9822

**References:** `U10` top / first in chain, `U11` bottom / second in chain  
**Part:** SK9822-EC20, 2×2mm, LCSC `C2909059`

The RGB status LEDs are intentionally retained in Rev A. They are small top/bottom-visible status/debug indicators, not the primary meltybrain heading indicator.

| Parameter | Value |
|---|---|
| Interface | APA102-compatible SPI-style data/clock |
| Power | 5V rail |
| Data buffer | `U8` SN74AHCT1G125, 3.3V input to 5V output |
| Clock buffer | `U9` SN74AHCT1G125, 3.3V input to 5V output |
| Output-enable control | `LED_OE_N` from SN74HC595 QD, pulled up by `R2` |
| Local bypass | `C16` = 100nF at U10, `C17` = 100nF at U11 |
| Worst-case LED current budget | ~61mA full white per LED, ~122mA for both |

Keep this subsystem populated for Rev A unless board area becomes impossible. It provides multi-color boot/error/mode indication on both sides of the robot without consuming extra direct XIAO GPIOs. Because the SK9822 chain shares the IMU SPI SCK/MOSI nets before the AHCT buffers, firmware must keep `LED_OE_N` disabled during normal IMU/latch SPI traffic and only enable the buffers when intentionally updating status LEDs. This avoids accidental LED updates during high-rate IMU bursts. Firmware must send two LED frames; duplicate the frame if top and bottom should show the same colour.

State/color mapping is firmware-defined. Suggested defaults:

| State | Colour | Pattern |
|---|---|---|
| Boot / no RC signal | White | Slow pulse |
| RC signal acquired, not spinning | Yellow | Solid |
| Spinning up | Yellow | Fast pulse |
| Heading lock acquired | Green | Solid |
| Drifting / manual correction | Cyan | Solid |
| Low battery | Red | Fast blink |
| Impact detected | Orange | Single flash |
| RC failsafe | Red | Solid |

---

## Meltybrain heading LED driver

**Connector:** `J2`  
**External module:** orange Tiny's LEDs 2-3S Micro LED / equivalent 2S-rated orange LED module  
**Driver topology:** module powered from switched 2S `VBUS`, low-side MOSFET switch controlled by XIAO edge pin D1/A1.

This is the primary visible heading marker. It is separate from the SK9822 status LED. Because the robot body will be printed in green filament, the default heading marker is a fixed orange LED module rather than a green or RGB heading LED.

At 4000RPM:

```text
1 revolution = 15ms
1 degree ~= 41.7us
100us pulse ~= 2.4 degree arc
300us pulse ~= 7.2 degree arc
500us pulse ~= 12 degree arc
```

Firmware must phase-lock the strobe to the estimated heading and start tuning with ~300-500us pulses. The LED must be off by default at boot/reset. Strobe generation must be a bounded hardware-timed one-shot using RP2350 PIO/timer logic with a hard maximum on-time; the main control loop should only arm/configure bounded pulses, not hold the GPIO high directly. This protects the TinySLED from overheating if firmware hangs or misses a state transition.

`J2` pinout:

| Pin | Signal | Notes |
|---:|---|---|
| 1 | `VBUS` | Switched 2S battery feed to TinySLED `+` pad |
| 2 | `HEAD_SW` | TinySLED `-` pad; MOSFET-switched return |

Driver parts:

| Function | Part | Notes |
|---|---|---|
| GPIO drive | XIAO D1/A1/GPIO41 | Edge/castellated pad only; avoids underside GPIO dependency |
| Gate stopper | `R16` = 100Ω | Between D1/A1 and Q1 gate |
| Gate pulldown | `R17` = 100kΩ | Holds LED off during boot/reset |
| Low-side switch | `Q1` AO3402 | Drain to `HEAD_SW`, source to GND |

Important notes:

- The selected 2-3S TinySLED module is expected to include its own current limiting; do not add a series LED resistor unless the selected module variant requires it.
- The heading LED current loop is `VBUS -> J2 pin 1 -> TinySLED -> J2 pin 2 -> Q1 -> GND`; route it away from IMU supplies and battery ADC routing.
- Keep the SK9822 RGB status LED for boot/error/mode colors; the TinySLED is the high-brightness heading marker only.


## Test points

Expose the following as 1mm solderable pads with silkscreen labels.

| Label | Signal | Why |
|---|---|---|
| `TP_VBAT` | `VBAT_SNS` | Battery divider output / ADC calibration |
| `TP_SWDIO` | `SWDIO` | Picoprobe/SWD debug data |
| `TP_SWDCK` | `SWDCK` | Picoprobe/SWD debug clock |
| `TP_GND` | GND | Scope/logic-analyzer/SWD ground reference |

---

## Pin assignment summary

| XIAO pad | Current signal | Direction | Notes |
|---|---|---|---|
| D0/A0/GPIO40 | `VBAT_SNS` | ADC in | Battery voltage divider |
| D1/A1/GPIO41 | `HEAD_LED` | GPIO out | Orange TinySLED MOSFET gate drive |
| D2/A2/GPIO42 | `SEL_OE_N` | GPIO out, active-low enable | Blanks/enables SN74HC595 latch outputs |
| D3/A3/GPIO43 | `SEL_LAT` | GPIO out | Latches the shifted SN74HC595 select byte |
| D4/SDA/GPIO6 | `DS1_IO` | bidir | AM32 channel 1 DSHOT/EDT via 33Ω |
| D5/SCL/GPIO7 | `DS2_IO` | bidir | AM32 channel 2 DSHOT/EDT via 33Ω |
| D6/TX/GPIO0 | `CRSF_TX` | UART out | To ELRS receiver |
| D7/RX/GPIO1 | `CRSF_RX` | UART in | From ELRS receiver |
| D8/SCK/GPIO2 | `SPI_SCK` | SPI out | IMUs, SN74HC595 latch, SK9822 buffer input |
| D9/MISO/GPIO4 | `SPI_MISO` | SPI in | IMU data return only |
| D10/MOSI/GPIO3 | `SPI_MOSI` | SPI out | IMUs, SN74HC595 latch, SK9822 buffer input |
| D11 | NC | — | Underside pad left unused in Rev A |
| D12 | NC | — | Underside pad left unused in Rev A |
| SWDIO | `SWDIO` | debug | Test pad |
| SWDCLK | `SWDCK` | debug | Test pad |
| 5V/VBUS | 5V | power in | Carrier AP63205 buck output; also powers the BetaFPV ELRS Lite receiver through the `U7` solder-down pads |
| 3V3 / 3V3_OUT | 3V3 | power out | Powers IMUs, latch, analog refs, and 3.3V logic |
| GND | GND | power | Common ground |

Runtime IO intentionally stays on XIAO edge/castellated pads. Underside GPIO/control pads are left NC unless a later revision explicitly accepts the assembly/rework tradeoff.

---

## Mass budget — carrier PCB, rough order

These are planning numbers only; measure final PCB and populated assembly.

| Component group | Qty | Estimated total |
|---|---:|---:|
| XIAO RP2350 module | 1 | ~3.0g |
| LSM6DSV320X + H3LIS331DL IMUs | 3 | ~0.15g |
| AP63205 buck IC + inductor + passives | 1 set | ~0.5g |
| SN74HC595 latch + pullups/decoupling | 1 set | ~0.1g |
| 2× SK9822 + AHCT buffers + passives | 1 set | ~0.15g |
| BetaFPV ELRS Lite receiver soldered on `U7` | 1 | ~0.5g |
| Orange TinySLED MOSFET gate driver | 1 set | ~0.05g, not including external LED/module/wires |
| Battery sense passives and essential test pads | — | ~0.1g |
| PCB substrate, 40×50mm, 1.0mm FR4 | 1 | ~3.0–3.3g |
| Solder + epoxy/strain relief | — | ~0.3g |
| **Carrier PCB total** |  | **~7.7g estimate** |

Removed versus older spec:

- No INA180 current-sense amplifier.
- No 5mΩ external shunt in the carrier BOM.
- No separate two-ESC signal connector pair.
- No protected piezo input in the current edge-pin-only Rev A schematic; D2/A2 is used for `SEL_OE_N`.

External/not included in carrier mass:

- Repeat AM32 Dual Brushless Drive ESC.
- External orange 2-3S TinySLED module and its wires.
- Piezo disc bonded to chassis.

---

## Fabrication notes

- **Layer count:** 2-layer is acceptable if layout keeps a clean ground return and compact buck loop; 4-layer is optional for easier grounding and routing.
- **Copper weight:** 1oz outer layers standard.
- **Surface finish:** ENIG recommended for LGA-16L IMUs and XIAO castellations; avoid HASL for the LGA pads.
- **Min trace/space:** 0.1mm / 0.1mm target for LGA fanout.
- **Soldermask:** both sides.
- **Assembly:** paste + reflow/hot air required for LGA-16L. Do not attempt iron-only assembly of the IMUs.
- **Stencil:** order a stainless stencil with the PCB.
- **Reinforcement:** epoxy fillets at XIAO corners and strain relief on all fly-lead exits after electrical test.

---

## Open items before fab

1. **Final IMU coordinates**  
   Board outline is now 40×50mm rectangular. Nominal IMU centroids are listed in the IMU placement table. After assembly, measure actual positions and update firmware constants.

2. **BetaFPV ELRS Lite receiver integration**  
   The receiver solders directly to the carrier `U7` footprint (pad order GND, 5V, TX/T, RX/R). Before soldering, re-verify the physical pad order on the actual receiver, plus firmware target/version, binding phrase, packet rate, telemetry ratio, and failsafe behavior.

3. **AM32 configuration**  
   Set profile `AM32_RR_ROBOT_DUAL_ESC_F421`, bidirectional drive, bidirectional DSHOT/EDT, current limits, motor direction, and correct motor pole count.

4. **Heading LED/module selection**  
   Confirm the exact orange 2-3S TinySLED / LED module variant, pad polarity, and mounting. Validate that it remains visible through/around the green chassis material; add a clear/frosted window or diffuser if needed. Confirm it has onboard current limiting; otherwise add a suitable series limiter.

5. **Heading strobe firmware safety**  
   Implement the TinySLED pulse as a hardware-timed one-shot with a hard maximum on-time. Verify reset/boot keeps Q1 off via `R17`, and verify a firmware hang cannot leave `HEAD_LED` asserted continuously.

6. **ESC BEC characterization**  
   Optional future work only. Measure BEC voltage/current/noise under motor load before considering deletion/DNP of the AP63205 buck.

7. **IMU readout firmware**  
   Implement optimized sequential IMU reads through the SN74HC595 select latch. Keep exactly one IMU selected at a time, update the latch only while `SEL_OE_N` blanks the outputs, and do not use simultaneous-CS reads unless the PCB is revised for separate MISO lines.

8. **IMU placement measurement**  
   After assembly, measure actual IMU centroids and axes relative to chassis centre and store calibration constants in firmware.

9. **Power integrity check**  
   Scope 5V, 3V3, and VBUS during heading LED strobes, DSHOT traffic, and motor spin-up. Ensure TinySLED pulses do not corrupt IMU reads, VBAT ADC readings, or reset the XIAO.

10. **H3LIS331DL shared-bus I2C-listening exposure**  
    The H3LIS331DL has no I2C-disable register bit (CTRL_REG4 = BDU/BLE/FS1/FS0/SIM only); whenever its CS is high it reverts to I2C mode and listens to `SPI_SCK`/`SPI_MOSI` as SCL/SDA. Bus traffic that mimics START + address `0x18/0x19` + W can make a deselected U5/U6 ACK onto MOSI or accept a phantom write into its own config registers. Firmware must set the LSM6DSV320X I2C/I3C-disable bit at init and periodically read back/verify H3LIS config registers; if field testing shows corruption, add per-sensor SCK|CS OR-gate clock gating or move to the Rev B parallel-MISO rework.
