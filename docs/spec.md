# Holy Guacamole — Carrier PCB Specification

**Document status:** Draft v1.3 — updated to match current `circuit.py` Rev A schematic  
**Robot:** Holy Guacamole — 1lb meltybrain antweight, MRCA full-combat  

---

## Overview

The carrier PCB is a purpose-built board for a Seeed XIAO RP2350 module. It is **not** a bare-RP2350 compute board: the XIAO provides the RP2350, flash, USB, crystal, and onboard 3.3V regulator. The carrier provides power conditioning, sensors, connectors, and robot-specific IO.

Primary carrier jobs:

- Mount the XIAO RP2350 flat as an SMD/castellated module; no XIAO pin headers.
- Generate a local regulated 5V rail from the switched 2S LiPo bus using an AP63205 fixed-5V buck regulator.
- Use the XIAO 3.3V rail for IMUs, GPIO expander, ELRS receiver, analog protection, and control logic.
- Route SPI to three H3LIS331DL high-G accelerometers.
- Use a MCP23S17 SPI GPIO expander for IMU chip-selects and SK9822 LED-output enable.
- Connect to the Repeat AM32 Dual Brushless Drive ESC using two direct bidirectional DSHOT/EDT lines.
- Keep independent battery voltage sensing on the carrier.
- Rely on AM32 bidirectional DSHOT / EDT for motor eRPM/current/voltage telemetry; no external Kelvin shunt in Rev A.
- Provide a dedicated orange 2-3S TinySLED meltybrain heading output using XIAO edge pin D1/A1 and one MOSFET low-side switch; no underside XIAO GPIOs are used for runtime IO.
- Provide protected piezo impact sensing, status LED, SWD pads, and scope/logic-analyzer test points.

The PCB mounts near the chassis centre. Final IMU coordinates must be measured from the actual chassis rotation centre and copied into firmware calibration constants.

---

## Current schematic reference designators

These names match the current SKiDL schematic in `circuit.py`.

| Ref | Function |
|---|---|
| `U1` | Seeed XIAO RP2350 SMD module |
| `U2` | AP63205 fixed 5.0V buck regulator |
| `U3` | MCP23S17 SPI GPIO expander |
| `U4`, `U5`, `U6` | H3LIS331DLTR high-G accelerometers |
| `U8`, `U9` | SN74AHCT1G125 3.3V-to-5V SK9822 data/clock buffers |
| `U10` | SK9822-EC20 2×2mm addressable status LED |
| `Q1` | AO3402 low-side MOSFET for orange TinySLED heading LED |
| `J1` | Switched 2S LiPo / VBUS carrier power input |
| `J2` | External orange 2-3S TinySLED heading LED connector |
| `J3` | Piezo impact sensor fly-lead connector |
| `J4` | Repeat AM32 dual ESC signal connector |
| `J6` | ELRS receiver connector |

`J5` from the older two-separate-ESC-connector version is retired.

---

## Physical constraints

| Parameter | Value |
|---|---|
| Board shape | Circular or rounded/lobed circular carrier |
| Board diameter target | **38mm baseline**, not 35mm |
| 35mm option | Treat as a stretch goal only after actual KiCad placement/routing proves it |
| Max board thickness | 1.0mm preferred; standard 1.6mm may violate chassis Z budget |
| Max component height above board | 2.5mm nominal, set by XIAO module height |
| Mounting | 3× M3 brass heat-set inserts in chassis, M3×6 SHCS from below |
| Connector exits | Radially outward via silicone wire fly-leads / solder pads, not fragile board-edge plug headers |
| Operating temperature | 0–60°C ambient expectation, with local motor/ESC heating nearby |
| Vibration/impact | Extreme; reinforce heavy/tall components and wire exits with epoxy or strain relief |

### IMU placement versus board diameter

The older spec targeted outer IMUs at 20mm radius while also targeting a 35mm circular board. Those two constraints are geometrically inconsistent for a centred circular board. A 38mm circular board has only a 19mm radius before component edge clearance.

Rev A layout rule:

- Use 38mm OD as the baseline mechanical envelope.
- Place IMUs as far outward as practical while preserving solder-mask clearance, routing, and assembly yield.
- If true 20mm IMU centroid radius is mandatory, the board outline needs local lobes or a larger local radius, or the sensor geometry must be revised.
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
2S LiPo
  -> Fingertech / main switch
      -> switched battery bus
          -> Repeat AM32 dual ESC power pads
          -> carrier J1 VBUS/GND
              -> AP63205 fixed 5.0V buck
                  -> 5V rail
                      -> XIAO 5V/VBUS pad
                      -> SK9822 status LED + AHCT buffers
                  -> XIAO onboard 3.3V regulator
                      -> H3LIS331DL IMUs
                      -> MCP23S17 expander
                      -> ELRS receiver
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
| Input voltage | 3.8–32V part capability; design VBUS is 2S LiPo, 6.0–8.4V |
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

Layout requirements:

- Place `C1`/`C2` tight to U2 VIN/GND.
- Keep the `SW` copper area compact.
- Keep the buck switch node and inductor away from IMUs, CRSF, piezo, and battery/heading ADC/test nodes.
- Use wide copper for VBUS and 5V where LED pulses can draw peak current.

---

## IMU array: 3× H3LIS331DL

**References:** `U4`, `U5`, `U6`  
**Part:** STMicroelectronics H3LIS331DLTR, LGA-16L 3×3mm, LCSC `C2655074`

### Placement geometry

All three IMUs share SPI SCK/MOSI/MISO and use independent active-low chip-selects generated by `U3` MCP23S17.

Nominal geometry intent:

| Sensor | Nominal angle | Nominal radius | Rationale |
|---|---:|---:|---|
| IMU-A | 0° / East | 12mm | Inner reference sensor with lower G loading |
| IMU-B | 90° / North | as far outward as layout allows, target up to 20mm | Orthogonal outer sensor for X/Y decomposition |
| IMU-C | 210° | as far outward as layout allows, target up to 20mm | Asymmetric placement breaks heading singularities |

G loading at 4000RPM:

| Radius | Centrifugal G |
|---:|---:|
| 12mm | ~216G |
| 18mm | ~324G |
| 20mm | ~360G |
| 400G limit at 20mm | ~4300RPM |

Do not blindly place outer IMUs beyond what the final board outline and package clearance allow. If the outer radius changes, update the firmware measurement model.

### H3LIS331DL configuration

| Parameter | Value |
|---|---|
| Range | ±400G |
| Interface | SPI mode 0, up to 10MHz |
| Output data rate | 1000Hz target |
| Axes used | X/Y in-plane; Z available in register data but not central to heading model |
| Reserved pins | Pin 10 to GND, pin 15 to Vdd |
| Interrupt pins | Unused/NC in current schematic |

### Decoupling

Current schematic has:

- `C8`, `C9`, `C10` = 100nF local capacitors, one per IMU.
- `C6` = 10uF shared 3.3V bulk capacitor for the sensor/control cluster.

ST guidance for H3LIS331DL supply bypassing calls for local 100nF plus bulk capacitance near Vdd. In layout, keep `C6` close to the IMU/3.3V cluster or add extra local 10uF if the shared bulk cap ends up far away.

### SPI wiring

| Signal | Source | Notes |
|---|---|---|
| `SPI_SCK` | XIAO D8/GPIO2 | Shared SPI clock |
| `SPI_MOSI` | XIAO D10/GPIO3 | Shared MOSI |
| `SPI_MISO` | XIAO D9/GPIO4 | Shared MISO |
| `CS_A` | MCP23S17 GPA0 | IMU-A active-low chip-select |
| `CS_B` | MCP23S17 GPA1 | IMU-B active-low chip-select |
| `CS_C` | MCP23S17 GPA2 | IMU-C active-low chip-select |

`R6`, `R7`, and `R8` are 33Ω series resistors from each IMU SDO to shared MISO for ringing and bus-contention limiting.

Each CS line has a 10kΩ pull-up (`R3`, `R4`, `R5`) so the IMUs remain deselected while the RP2350 and MCP23S17 boot.

### Axis orientation convention

Mount each chip so:

- chip X axis points radially outward from the rotation centre;
- chip Y axis points tangentially in the defined positive rotation direction.

Verify against the H3LIS331DL datasheet axis diagram before fabrication. Wrong axis orientation is hard to debug after assembly.

---

## SPI GPIO expander

**Reference:** `U3`  
**Part:** MCP23S17T-E/SS, LCSC `C128577`

The XIAO edge pads are pin-limited, so the carrier uses a SPI GPIO expander.

| Expander function | Signal |
|---|---|
| SPI chip select from XIAO | `EXP_CS_N`, XIAO D3/A3/GPIO43 |
| IMU-A select | `CS_A` |
| IMU-B select | `CS_B` |
| IMU-C select | `CS_C` |
| SK9822 level-shifter output enable | `LED_OE_N` |

Boot-safe pull-ups:

- `R1`: expander CS inactive while XIAO boots.
- `R2`: AHCT LED buffers disabled while XIAO/MCP23S17 boot.
- `R3`/`R4`/`R5`: IMU chip-selects inactive while MCP23S17 GPIOs are high-Z.

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
- Keep DSHOT lines direct from RP2350-capable GPIOs; do not route through MCP23S17.
- **Firmware must use DSHOT600** for normal bidirectional DSHOT/EDT operation at ~4000–4300RPM. DSHOT300 is allowed only for bench/low-speed testing because the effective bidirectional command/telemetry update rate is marginal near strike RPM.
- Bidirectional DSHOT/EDT returns eRPM and extended telemetry over the same signal wires; no extra telemetry UART is required in Rev A.
- Configure AM32 motor pole count correctly. For a 14-pole outrunner, pole pairs = 7 and mechanical RPM = eRPM / 7. Verify actual motor magnet pole count instead of guessing.
- ESC BEC output is not connected to this carrier in Rev A.

High-current ESC battery and motor phase wiring must not pass through the carrier PCB. The carrier only handles logic-level DSHOT/EDT and its own VBUS feed.

---

## CRSF / ELRS

**Connector:** `J6`

| J6 pin | Signal | Notes |
|---:|---|---|
| 1 | 3V3 | Receiver power from XIAO 3.3V rail; verify receiver supports 3.3V |
| 2 | GND | Receiver ground |
| 3 | `CRSF_TX` | XIAO D6/GPIO0 -> receiver |
| 4 | `CRSF_RX` | receiver -> XIAO D7/GPIO1 |

CRSF caveat:

- CRSF is commonly described as inverted UART at 420000 baud, but receiver behavior varies.
- Prefer an ELRS receiver or pad configuration that exposes non-inverted CRSF if available.
- If the chosen receiver only exposes inverted CRSF, handle inversion in RP2350 PIO/firmware or add a hardware inverter in a later revision.
- Rev A schematic has no discrete CRSF inverter.

Receiver placement: off-PCB on chassis wall for antenna clearance, away from the buck inductor and motor phase wires.

---

## Analog / event inputs

### Battery voltage sense

The carrier keeps an independent battery divider even though the ESC can provide telemetry. This gives pack voltage during bring-up and if ESC telemetry is unavailable.

| Parameter | Value |
|---|---|
| XIAO ADC pin | A0/D0/GPIO40 |
| Net | `VBAT_SNS` |
| Divider high-side | `R9` = 100kΩ from VBUS |
| Divider low-side | `R10` = 33kΩ to GND |
| Filter | `C12` = 100nF to GND |
| ADC voltage at 8.4V pack | ~2.08V |
| ADC voltage at 6.0V pack | ~1.49V |

Use this for independent low-battery warning and telemetry. Firmware can fuse/compare this with AM32 EDT voltage.

### Current sensing

There is **no INA180 / Kelvin shunt current-sense circuit in Rev A**.

Current/eRPM telemetry path:

- AM32 bidirectional DSHOT provides eRPM feedback per motor.
- AM32 Extended DSHOT Telemetry can provide ESC voltage/current/temperature data when supported/configured.
- ESC current limiting remains local to the ESC.

If future testing shows AM32 current telemetry is insufficient, add an external inline shunt and INA180 in a later revision. Do not route motor current through this carrier PCB.

### Piezo contact sensor

**Connector:** `J3`

| Parameter | Value |
|---|---|
| Element | 20mm passive piezo disc, chassis-bonded |
| XIAO ADC pin | A2/D2/GPIO42 |
| Net | `PIEZO` |
| Pulldown | `R11` = 1MΩ to GND |
| Filter | `C13` = 10nF to GND |
| Clamp | `D1` = BAT54S Schottky pair to GND and 3V3 |

Piezo elements can generate voltage spikes well beyond 3.3V during impact. The Schottky clamp and pulldown are required to protect and bias the ADC input.

---

## Status LED: SK9822

**Reference:** `U10`  
**Part:** SK9822-EC20, 2×2mm, LCSC `C2909059`

This is a small top-visible status LED, not the primary meltybrain heading indicator.

| Parameter | Value |
|---|---|
| Interface | APA102-compatible SPI-style data/clock |
| Power | 5V rail |
| Data buffer | `U8` SN74AHCT1G125, 3.3V input to 5V output |
| Clock buffer | `U9` SN74AHCT1G125, 3.3V input to 5V output |
| Output-enable control | `LED_OE_N` from MCP23S17 GPA3, pulled up by `R2` |
| Local bypass | `C16` = 100nF |
| Worst-case LED current budget | ~61mA full white |

Because the SK9822 shares the IMU SPI SCK/MOSI nets before the AHCT buffers, firmware must keep `LED_OE_N` disabled during normal IMU/MCP23S17 SPI traffic and only enable the buffers when intentionally updating the status LED. This avoids accidental LED updates during high-rate IMU bursts.

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
- The heading LED current loop is `VBUS -> J2 pin 1 -> TinySLED -> J2 pin 2 -> Q1 -> GND`; route it away from IMU supplies, piezo, and battery ADC routing.
- `TP_HEAD` probes `HEAD_LED` before `R16` for timing verification without loading the LED current path.
- Keep the SK9822 status LED for mode/error colors; the TinySLED is the high-brightness heading marker only.


## Test points

Expose the following as 1mm solderable pads with silkscreen labels.

| Label | Signal | Why |
|---|---|---|
| `TP_SCK` | `SPI_SCK` | Verify shared SPI clock |
| `TP_CS_A` | `CS_A` | IMU-A chip-select |
| `TP_CS_B` | `CS_B` | IMU-B chip-select |
| `TP_CS_C` | `CS_C` | IMU-C chip-select |
| `TP_MISO` | `SPI_MISO` | Verify IMU data return |
| `TP_DS1` | `DSHOT1` | AM32 channel 1 bidirectional DSHOT/EDT waveform |
| `TP_DS2` | `DSHOT2` | AM32 channel 2 bidirectional DSHOT/EDT waveform |
| `TP_CRSF_RX` | `CRSF_RX` | Receiver packets into XIAO |
| `TP_CRSF_TX` | `CRSF_TX` | CRSF telemetry/control packets out |
| `TP_VBAT` | `VBAT_SNS` | Battery divider output |
| `TP_HEAD` | `HEAD_LED` | Orange TinySLED strobe timing before MOSFET gate resistor |
| `TP_PIEZO` | `PIEZO` | Impact sensor waveform |
| `TP_SWDIO` | `SWDIO` | Picoprobe/SWD debug data |
| `TP_SWDCK` | `SWDCK` | Picoprobe/SWD debug clock |
| `TP_GND` | GND | Scope/logic-analyzer ground reference |
| `TP_3V3` | 3V3 | XIAO 3.3V rail check |
| `TP_5V` | 5V | AP63205 buck output check |

---

## Pin assignment summary

| XIAO pad | Current signal | Direction | Notes |
|---|---|---|---|
| D0/A0/GPIO40 | `VBAT_SNS` | ADC in | Battery voltage divider |
| D1/A1/GPIO41 | `HEAD_LED` | GPIO out | Orange TinySLED MOSFET gate drive |
| D2/A2/GPIO42 | `PIEZO` | ADC in | Protected piezo impact input |
| D3/A3/GPIO43 | `EXP_CS_N` | GPIO out | MCP23S17 SPI chip-select |
| D4/SDA/GPIO6 | `DS1_IO` | bidir | AM32 channel 1 DSHOT/EDT via 33Ω |
| D5/SCL/GPIO7 | `DS2_IO` | bidir | AM32 channel 2 DSHOT/EDT via 33Ω |
| D6/TX/GPIO0 | `CRSF_TX` | UART out | To ELRS receiver |
| D7/RX/GPIO1 | `CRSF_RX` | UART in | From ELRS receiver |
| D8/SCK/GPIO2 | `SPI_SCK` | SPI out | IMUs, MCP23S17, SK9822 buffer input |
| D9/MISO/GPIO4 | `SPI_MISO` | SPI in | IMUs/MCP23S17 return |
| D10/MOSI/GPIO3 | `SPI_MOSI` | SPI out | IMUs, MCP23S17, SK9822 buffer input |
| D11 | NC | — | Underside pad left unused in Rev A |
| D12 | NC | — | Underside pad left unused in Rev A |
| SWDIO | `SWDIO` | debug | Test pad |
| SWDCLK | `SWDCK` | debug | Test pad |
| 5V/VBUS | 5V | power in | Carrier AP63205 buck output |
| 3V3 / 3V3_OUT | 3V3 | power out | Powers IMUs, expander, receiver, analog refs |
| GND | GND | power | Common ground |

Runtime IO intentionally stays on XIAO edge/castellated pads. Underside GPIO/control pads are left NC unless a later revision explicitly accepts the assembly/rework tradeoff.

---

## Mass budget — carrier PCB, rough order

These are planning numbers only; measure final PCB and populated assembly.

| Component group | Qty | Estimated total |
|---|---:|---:|
| XIAO RP2350 module | 1 | ~3.0g |
| H3LIS331DL IMUs | 3 | ~0.15g |
| AP63205 buck IC + inductor + passives | 1 set | ~0.5g |
| MCP23S17 expander + pullups/decoupling | 1 set | ~0.1g |
| SK9822 + AHCT buffers + passives | 1 set | ~0.1g |
| Orange TinySLED MOSFET gate driver | 1 set | ~0.05g, not including external LED/module/wires |
| Battery/piezo passives and test pads | — | ~0.1g |
| PCB substrate, 38mm dia, 1.0mm FR4 | 1 | ~2.0–2.2g |
| Solder + epoxy/strain relief | — | ~0.3g |
| **Carrier PCB total** |  | **~6.2g estimate** |

Removed versus older spec:

- No INA180 current-sense amplifier.
- No 5mΩ external shunt in the carrier BOM.
- No separate two-ESC signal connector pair.

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

1. **Final board outline and IMU coordinates**  
   Resolve 38mm circular outline versus desired outer IMU radius. If outer sensors cannot reach 20mm centroid radius, choose final coordinates and update firmware constants.

2. **CRSF inversion for chosen ELRS receiver**  
   Confirm whether the receiver exposes non-inverted CRSF. If not, plan RP2350 PIO inversion or add a hardware inverter in Rev B.

3. **AM32 configuration**  
   Set profile `AM32_RR_ROBOT_DUAL_ESC_F421`, bidirectional drive, bidirectional DSHOT/EDT, current limits, motor direction, and correct motor pole count.

4. **Heading LED/module selection**  
   Confirm the exact orange 2-3S TinySLED / LED module variant, pad polarity, and mounting. Validate that it remains visible through/around the green chassis material; add a clear/frosted window or diffuser if needed. Confirm it has onboard current limiting; otherwise add a suitable series limiter.

5. **Heading strobe firmware safety**  
   Implement the TinySLED pulse as a hardware-timed one-shot with a hard maximum on-time. Verify reset/boot keeps Q1 off via `R17`, and verify a firmware hang cannot leave `HEAD_LED` asserted continuously.

6. **ESC BEC characterization**  
   Optional future work only. Measure BEC voltage/current/noise under motor load before considering deletion/DNP of the AP63205 buck.

7. **IMU placement measurement**  
   After assembly, measure actual IMU centroids and axes relative to chassis centre and store calibration constants in firmware.

8. **Power integrity check**  
   Scope 5V, 3V3, and VBUS during heading LED strobes, DSHOT traffic, and motor spin-up. Ensure TinySLED pulses do not corrupt IMU reads, piezo/VBAT ADC readings, or reset the XIAO.
