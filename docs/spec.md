# Holy Guacamole: Carrier PCB Specification

**Document status:** Rev B draft 2.0. Tracks the KiCad schematic `hardware/guac.kicad_sch` (rev `2.0-draft`). The KiCad schematic is the source of truth; `hardware/circuit.py` is a stale SKiDL sketch and no longer matches it.
**Robot:** Holy Guacamole, 1 lb meltybrain antweight, MRCA full combat
**Previous revision:** Rev A (v1.3c, 40 × 50 mm, fly-lead pads, solder-down receiver). See git history for that text.

---

## What changed from Rev A

| # | Change | Why |
|---|---|---|
| 1 | The carrier is now the power distribution board. Battery and switch loop land on vertical XT30s; the ESC battery feed leaves from 20 AWG SMD lap pads at the S edge. | Removes the J1 pigtail, the 16 AWG splices, and the separate PDB. This deliberately reverses the Rev A rule that high current never touches the carrier. |
| 2 | Latching JST-GH connectors for the ESC signal, the receiver, and both TinySLEDs. | Solder pads and fly-leads were the weakest joints in impacts. |
| 3 | ELRS receiver moves off-board to the S pocket on a JST-GH harness. `U7` is gone; `J5` replaces it, with ESD clamps `D5`/`D6`. | Gets the antenna out of the battery's shadow and off the board's copper. |
| 4 | 100 µF / 25 V polymer tantalum bulk capacitor `C21` on VBUS near the ESC feed. | Absorbs ESC regen and hot-plug ringing on the now board-mounted bus. |
| 5 | SK9822 status-LED chain deleted (`U8`, `U9`, `U10`, `U12`, `C14`–`C17`, `R14`, `R15`) along with its enable pull-up `R21`. `U11` QD is now NC. | Neither LED has a window in the chassis. The TinySLED blinks status codes instead. |
| 6 | Duplicate CS pull-ups `R19`/`R20` deleted. | `R4`/`R5` already do the job. |
| 7 | **Bug fix:** `R6`/`R7`/`R8` (IMU SDO series resistors) now land on `SPI_MISO`. In Rev A they were wired to `SPI_MOSI` in both the schematic and the routed PCB, so `SPI_MISO` (XIAO D9) connected to nothing and every IMU drove its SDO onto the master's MOSI line. | Rev A boards cannot read the IMUs over standard SPI without a bodge (cut the three R-to-MOSI traces and jumper them to D9). |
| 8 | New 40 × 76 mm outline centred on the spin axis, ends clamped under the v33 end ledges; 1.6 mm FR4, 2 oz copper; four M2 screws into the ledges. | See [Board outline](#board-outline-and-mechanical). |
| 9 | The ESC BEC stays isolated, as in Rev A. | Unchanged policy. |

Two suggestions from the review were **not** taken as written:

- **TVS placement.** The review said to move `D2` to the battery entry. It stays on `VBUS` (the switched side). The big transients on this bus come from the ESC (regen braking in bidirectional mode), and those land on `VBUS`. With the switch closed the two nodes are the same copper anyway; with it open, the carrier is unpowered and needs no clamp. Physically, `D2` sits in the SE corridor between `J6` and the IMU array; `C21` is about 12 mm from `J1`.
- **Bottom TinySLED connector on the underside.** The board sits 0.32 mm above the bottom plate, so nothing can go on the underside. The TinySLED socket `J2` sits on the top side in the SW. Both LEDs share it through a Y-splice in the harness (they were already in parallel), so `J3` is gone.
- **≤ 6 mm under the battery.** v33b leaves 4.7 mm on a 1.6 mm board, but only in the 12 mm strip under the pack. The side corridors are open to z 25.5. See the [Z budget](#z-budget).
- **Foam under the board.** The bottom plate is now recessed and sits 0.32 mm below the board. No foam; flush pads only.

The MR30 suggestion is a harness item (motor phases go to the ESC, not the carrier), so it is listed under [Harness](#harness), not in the schematic.

---

## Overview

The carrier is a purpose-built board for a Seeed XIAO RP2350 module. The XIAO provides the RP2350, flash, USB, crystal, and the 3.3 V regulator. The carrier provides:

- Battery, switch-loop, and ESC power distribution on board copper.
- A 5 V buck rail from the switched LiPo bus: 3S HV (GNB 380 mAh, 55 × 17 × 20 mm, 13.05 V full, 11.4 V nominal); 2S still supported by the UVLO jumper.
- SPI to one inner LSM6DSV320X 6-axis IMU and two outer H3LIS331DL high-G accelerometers, with chip-selects from a SPI-loaded SN74HC595 latch.
- Two direct bidirectional DSHOT/EDT lines to the Repeat AM32 dual ESC.
- A CRSF UART and 5 V feed to an off-board ELRS receiver.
- Independent battery voltage sensing.
- A MOSFET low-side driver for two paralleled orange TinySLED heading LEDs.
- A debug edge with SWD, a UART, VBAT, and GND.

Runtime IO stays on the XIAO edge pads; underside XIAO pads are NC.

---

## Reference designators (KiCad, rev 2.0-draft)

| Ref | Function | Footprint |
|---|---|---|
| `U1` | Seeed XIAO RP2350 SMD module | `Library:XIAO-RP2350-SMD` |
| `U2` | AP6330x 3 A synchronous buck, 5.0 V via divider (see note) | TSOT-23-6 |
| `U4` | LSM6DSV320XTR inner IMU | LGA-14 |
| `U5`, `U6` | H3LIS331DLTR outer high-G accelerometers | LGA-16 3 × 3 |
| `U11` | SN74HC595PWR chip-select latch | TSSOP-16 |
| `Q1` | AO3402 TinySLED low-side switch | SOT-23 |
| `J1` | ESC battery feed, two 2.6 × 4.0 mm SMD lap pads for 20 AWG; pad 1 VBUS (W), pad 2 GND (E) | `Device:SolderLap_20AWG_1x02_2.6x4.0mm_P3.2mm` (project library) |
| `J2` | TinySLEDs, top and bottom on one Y-spliced harness, JST-GH 2-pin | `JST_GH_SM02B-GHS-TB` |
| `J4` | AM32 ESC signal, JST-GH 4-pin | `JST_GH_SM04B-GHS-TB` |
| `J5` | ELRS receiver harness, JST-GH 4-pin | `JST_GH_SM04B-GHS-TB` |
| `J6` | Battery, XT30 male, vertical | `AMASS_XT30UPB-M` |
| `J7` | Switch loop, XT30 female, vertical | `AMASS_XT30UPB-F` |
| `JP1` | UVLO select solder jumper (open / 2S / 3S) | 3-pad jumper |
| `L1` | 5.6 µH Bourns SRP6060FA | SRP6060FA |
| `C21` | 100 µF 25 V polymer tantalum, ≤ 4.3 mm tall (fits under the battery) | `CP_EIA-7343-43_Kemet-X` |
| `D2` | SMAJ15CA bidirectional TVS on VBUS | SMA |
| `D3`, `D4` | ESD clamps on DSHOT1/DSHOT2 at `J4` | SOD-523 |
| `D5`, `D6` | ESD clamps on CRSF_RX/CRSF_TX at `J5` | SOD-523 |
| `TP10`, `TP13`–`TP15` | VBAT_SNS, SWDIO, SWDCK, GND test pads | 1 mm pad |

**Buck part: AP63301WU-7** (forced PWM). Both parts share one datasheet ([Diodes AP63300/AP63301](https://www.diodes.com/datasheet/download/AP63300_AP63301.pdf)), pinout, 0.8 V ±1% reference, 500 kHz clock, EN thresholds (1.18 V rising, 1.09 V falling, 1.5/5.5 µA pull-up), and the `R27`/`R28`/`C18` network. They differ only in light-load behaviour:

| | AP63300 | AP63301 |
|---|---|---|
| Light-load mode | PFM bursts, 930 mA peak inductor current, 60 mA zero-cross | PWM at every load |
| Switching frequency | 500 kHz ±6% spread spectrum in PWM; variable and load-dependent in PFM | Fixed 500 kHz |
| Quiescent current | 22 µA | 280 µA |

The carrier's 5 V load is about 100–150 mA (XIAO plus receiver), which would keep an AP63300 in PFM most of the time. That means 930 mA current bursts through `L1` at an irregular rate, next to three accelerometers, the VBAT ADC, and the CRSF line. The AP63301's fixed 500 kHz is easier to filter and to recognise on a scope. The extra 0.26 mA is about 0.07% of the 380 mAh pack per hour, so it doesn't matter. The AP63301 is what the procurement files already order (Mouser `621-AP63301WU-7`); the KiCad value now matches.

Free refs from deletions: `R14`, `R15`, `R19`, `R20`, `R21`, `C14`–`C17`, `U7`–`U10`, `U12`, `J3`. Do not reuse them in this revision, so old BOMs and photos stay unambiguous.

---

## Power architecture

```text
3S HV LiPo, 9.0–13.05 V
  -> J6 XT30-M (battery, SE corridor)        net VBAT_RAW
      -> J7 XT30-F (switch loop, NW corridor) pin 2 VBAT_RAW out
          -> Fingertech switch on a short XT30 pigtail, in its frame socket
      <- J7 pin 1                              net VBUS (switched)
          -> C21 100 µF bulk + D2 SMAJ15CA     at the S edge
          -> J1 pads -> AM32 dual ESC battery pads (20 AWG, 4-8 A per channel)
          -> U2 buck -> 5V
                -> XIAO 5V pad -> XIAO 3V3 -> IMUs, latch, pull-ups
                -> J5 pin 2 -> ELRS receiver
          -> R9/R10 divider -> VBAT_SNS (XIAO A0)
          -> J2 pin 1 -> both TinySLEDs -> Q1 -> GND
```

`J6` and `J7` polarity follows the AMASS footprint marks: pad 1 is the "−" side, pad 2 the "+" side. For `J6` that means pad 1 GND, pad 2 VBAT_RAW. `J7` carries no ground: pad 1 is VBUS (switch return), pad 2 is VBAT_RAW. **Silkscreen `J7` as "SW" with both pads labelled, not "+/−"**, so nobody plugs a battery into it.

Gender convention: the battery lead carries the female XT30, so the board gets the male (`J6`). The switch-loop socket is live from the battery, so the board side is female (`J7`) and the switch pigtail is male.

### Copper and current

| Item | Rule |
|---|---|
| Copper weight | 2 oz both layers (`project.toml`) |
| Peak current | Repeat AM32 at antweight: 4–8 A per channel, so about 16 A worst-case burst on VBUS/GND |
| VBAT_RAW, VBUS | Netclass `Power_Main`: 1.5 mm minimum track, 0.3 mm clearance, poured on both layers between `J6`, `J7`, `J1`, `C21` |
| GND | Poured on both layers, stitched; the high-current return path from `J1` to `J6` must not run under the IMU array |
| Via stitching | At least six 0.4 mm vias per power-path layer change |

The buck input caps (`C1`, `C19`, `C20`, `C2`) take VBUS from the pour, not from the ESC path. Route the ESC current loop (`J6` → `J7` → `J1` and back) along the board's edge strip, away from `U4`–`U6` and the `VBAT_SNS` divider.

### ESC BEC policy

The Repeat AM32 BEC stays **isolated**. Do not tie it to the carrier 5 V rail. Reasons: a known 5 V source on the controller, independence if the ESC resets, and no BEC noise in the IMU domain. Revisit only after scoping BEC voltage and noise under motor load.

### Buck regulator

| Parameter | Value |
|---|---|
| Part | AP63301WU-7, forced PWM (see buck note above), TSOT-23-6 |
| Input | 3.8–32 V part rating; design VBUS 9.0–13.05 V (3S HV). 2S (6.0–8.4 V) still works |
| Output | 5.0 V set by `R27` 158 kΩ / `R28` 30.1 kΩ, `C18` 47 pF feed-forward |
| Inductor | `L1` 5.6 µH Bourns SRP6060FA |
| Input caps | `C1`, `C19`, `C20` 22 µF 25 V 0805 + `C2` 100 nF |
| Output caps | `C4`, `C5` 22 µF |
| Bootstrap | `C3` 100 nF |
| UVLO | `JP1`: **bridge 2-3 for this pack** = 3S (`R25`/`R26`, about 8.85 V off / 9.92 V on, so it cuts at about 2.95 V/cell). 1-2 = 2S (`R23`/`R24`, 5.96 / 6.66 V). Open = bypass |
| Input-cap margin | At 13.05 V each Samsung `CL21A226MAYNNNE` keeps a little under the 4.4 µF it has at 12.6 V, so the three-cap worst case is about 10 µF, right at the reference design value. Acceptable; use a 35 V 22 µF 0805 (for example Murata GRM21BR6YA226ME43) for more margin |

Keep the SW node compact, take FB from the `C4`/`C5` node, and keep `L1` and SW away from the IMUs and `VBAT_SNS`. `L1` is the tallest part after the XT30s; stake it (see [Impact hardening](#impact-hardening)).

---

## Board outline and mechanical

Geometry is derived from chassis v33 rev B and confirmed against v34 (`holy_guacamole_v34.zip`), which is built around this board. Outputs and scripts live in `cad/rev2/` (`board_outline.dxf`, `keepout.dxf`, `README.md`); the older `body.step` analysis is archived in `cad/rev2/stale_bodystep/` and `cad/rev2/stale_v33a/`. If this section and `cad/rev2/README.md` disagree, the README wins.

| Parameter | Value |
|---|---|
| Outline | 40.0 × 76.0 mm, x −20…+20, y −38…+38, corner R1.5, centred on the spin axis. USB notch in the N edge at x 0.4…13.0 from y 29.2 (clears the v33 USB plug channel) |
| Origin | Spin axis. +Y points N |
| Thickness | 1.6 mm FR4 (1.2 mm if the XIAO-under-battery margin is too tight, see Z budget) |
| Mounting | 4 × M2 into 3 mm heat-sets in the end ledges: (±16.6, +34.5), (±17.0, −34.5) (south holes moved out in v34 for a 1.9 mm wall to the groove). 2.2 mm drill, 4.5 mm keepout |
| Board bottom | z 0.9 (unchanged from v33) |
| Underside | Nothing but flush bottom-copper test pads (nothing taller than solder mask). The gap to the bottom plate is 0.32 mm; no foam |
| Layers | 2 |
| Finish | ENIG (LGA pads; change `project.toml` from HASL at order time) |

### Chassis changes this outline needs

1. A recess in the underside of each end ledge: x ±20.5, |y| 29.9…38.5, from z −1 to board top + 0.1. This replaces the v33 tab pockets and M3 inserts; the board still drops in from below.
2. Four M2 heat-set bores (≤ 3.7 mm deep with a 1.6 mm board) at the hole positions above.
3. New bottom plate: 5 mm through-holes for the M2 heads (a 1.0 mm head sits inside the plate thickness), and drop the old 6.5 mm tab-screw holes.
4. Mirror the S-ledge wire groove to x −4.5…+13.5 and turn the ESC 180°, so its BAT/GND corner is on the E side. The receiver lead drop at x ±3 stays.

### Z budget

Board bottom at z 0.9; bottom plate top at z 0.58 (in a 0.6 mm pocket); ledge and battery floor at z 7.2. The battery (v3.4c) is the GNB 3S 380, 55 × 17 × 20 mm, at x ±8.5, y −23.2…+31.6, with its leads and XH balance plug leaving the S end. It covers a 17 mm strip of the board. A cross-beam under its S end (y −24.8…−19.8, z 4.0…7.2) limits parts there to 1.2 mm.

| | 1.2 mm board | 1.6 mm board |
|---|---:|---:|
| Board top | 2.10 | 2.50 |
| Max part height under the battery | 5.10 | **4.70** |
| XIAO + USB-C margin to battery floor (only the part still under the pack) | 0.80 | **0.40** |
| Max part height in the motor-screw key band | 4.43 | 4.03 |
| Gap to the bottom plate | 0.32 | 0.32 |

| Region | Height limit above a 1.6 mm board |
|---|---|
| Battery strip, \|x\| ≤ 6.5 | 4.7 mm |
| Side corridors, \|x\| 6.5…20.5 | about 23 mm (open to the rib shelves at z 25.5) |
| Motor-screw key band, \|y\| ≤ 8, in the corridors | about 4 mm |
| Motor-lead entries, y −25…−15, z 9.8…19.2 | about 7 mm |
| Ledge-clamped ends, \|y\| ≥ 29.9 | none (no top parts) |

`L1` (6 mm) goes in the NW corridor. `C21` is now a 7343-43 polymer tantalum (≤ 4.3 mm), so it fits in the battery strip in the S, about 12 mm from `J1`. A 25 V polymer part at 13.05 V is at 52% of rating, inside the usual 80% derating for polymer tantalum. Confirm a real 100 µF / 25 V part number in that case size before ordering; two 47 µF in parallel are fine if 100 µF isn't stocked.

USB runs through a ribbon extension with a slim male end, from the XIAO to the USB-C female on the shelves (z 19.4…21.4) under the top-plate slot.

### Placement (agreed with the chassis designer; exact coordinates in `cad/rev2/README.md`)

| Region | Contents |
|---|---|
| NE corridor, offset | XIAO, as far into the corridor as its 17.5 mm width allows, USB-C end in the plug channel (x 0.7…12.7) under the N ledge |
| NW corridor | `L1` (y 11…18) |
| Battery strip, S | `C21` |
| SE key band | `D2` |
| NW corridor | `J7` switch-loop XT30, near the switch at (−5, 50.5) |
| SE corridor, above the ESC pads | `J6` battery XT30, clear of the key band and the motor-lead entries |
| S gap, SE | `J1` ESC power lap pads (south of the beam), `J4` ESC signal. The ESC (turned 180° in v34) stands against the S bay wall with BAT/GND on the E side; its leads drop through the mirrored groove |
| W corridor, north of the beam | `J2` TinySLED socket at (−14.0, −16.3), opening N; plug and Y-splice north of it under the L-key sweep. The LED leads come up from the SW channel mouth (keep it clear) |
| S, near x 0 | `J5` receiver harness; the leads come down beside the ESC into the groove at x ±3 |
| Centre | IMU array on the spin axis |
| \|y\| > 29.9 | Nothing on top (clamped under the ledges) |

A mated XT30 stands about 21 mm, topping out near z 23.5, under the 26.5 side shelves; route the 16 AWG off sideways.

### Debug access

With the bottom plate off, only the underside and the four screws are reachable; the E and W edges sit 0.5 mm from the walls and the ends are under the ledges. So the debug pads (`TP13` SWDIO, `TP14` SWDCK, `TP15` GND, `TP10` VBAT_SNS, plus pads on `CRSF_TX`/`CRSF_RX` and VBUS) go on the **bottom copper as flush, unpopulated pads** with nothing taller than solder mask. That is the one exception to "nothing on the underside". USB through the chimney works with the top plate off and the battery in.

### IMU placement

The array stays centred on the spin axis. Nominal intent is unchanged:

| Sensor | Angle | Radius | Note |
|---|---:|---:|---|
| `U4` LSM6DSV320X | 0° | 12 mm | Inner reference with gyro, about 216 g at 4000 rpm |
| `U5` H3LIS331DL | 90° | 18 mm | About 324 g |
| `U6` H3LIS331DL | 210° | 18 mm | Asymmetric, breaks heading singularities |

With the v33b placement (`cad/rev2/README.md`), the nominal array puts U5 under the XIAO. Rotating the **whole array 166° CCW** clears everything (only 164–168° works): U4 (−11.64, 2.90), U5 (−4.35, −17.47), U6 (17.30, 4.96). Firmware adds 166° to each nominal angle (0/90/210 become 166/256/16). The window is 152–168° with J2 opening N; moving J2, J6 or C21 can close it, so re-check after any change. Firmware must use **measured** post-assembly IMU coordinates.

Mount each chip with X radial outward and Y tangential in the positive rotation direction; verify against the datasheet axis diagrams.

---

## Impact hardening

1. 1.6 mm board, four mounting points.
2. No MLCC within 2 mm of a mounting hole or 1 mm of an edge. Orient 0805 caps parallel to the nearest edge. Use soft-termination parts for `C1`, `C19`, `C20`, `C4`, `C5` where available (for example Murata GCJ / KEMET FT-CAP series).
3. Stake `L1`, `C21`, and the XIAO corners with epoxy after electrical test.
4. Conformal-coat the whole board, masking the GH sockets, XT30 pins, USB-C, and test pads.
5. A zip-tie strain-relief slot (about 1.2 × 3 mm) beside every connector: `J1`, `J2`, `J4`, `J5`, `J6`, `J7`.
6. Silkscreen polarity at every connector.

---

## IMU array

All three IMUs share `SPI_SCK`, `SPI_MOSI`, and `SPI_MISO`. Each SDO reaches `SPI_MISO` through a 33 Ω series resistor (`R6`, `R7`, `R8`). Chip-selects come from `U11`.

| Signal | XIAO pin | Notes |
|---|---|---|
| `SPI_SCK` | D8 / GPIO2 | Pulled down by `R22` 100 kΩ |
| `SPI_MOSI` | D10 / GPIO3 | Also the latch serial input |
| `SPI_MISO` | D9 / GPIO4 | IMU data return; fixed in Rev B |
| `CS_A` / `CS_B` / `CS_C` | `U11` QA / QB / QC | Pulled up by `R11` / `R4` / `R5` 10 kΩ |

Decoupling: `C8`, `C11` (U4 VDD, VDDIO), `C9` (U5), `C10` (U6), each 100 nF; `C6` and `C13` 10 µF near the outer sensors.

Firmware must select one IMU at a time; a three-IMU read set takes about 15–30 µs at 10 MHz, which is about 0.7° of skew at 4000 rpm.

### H3LIS331DL shared-bus I2C exposure

The H3LIS331DL has no I2C-disable bit. With its CS high it listens to `SPI_SCK`/`SPI_MOSI` as SCL/SDA. The bus therefore runs **SPI Mode 0** (SCK idle low): in Mode 0, SDA only changes while SCL is low, so an I2C START can never form. `R22` holds SCK low through boot and reset. Mode 3 must not be used. Firmware sets the LSM6DSV320X `IF_CFG.I2C_DISABLE` bit and periodically reads back the H3LIS config registers.

---

## Chip-select latch (`U11` SN74HC595)

| Function | Signal |
|---|---|
| `/OE` | `SEL_OE_N`, XIAO D2, pulled up by `R1` 10 kΩ |
| `RCLK` | `SEL_LAT`, XIAO D3, pulled down by `R18` 100 kΩ |
| `SER` | `SPI_MOSI` |
| `SRCLK` | `SPI_SCK` |
| QA / QB / QC | `CS_A` / `CS_B` / `CS_C` |
| QD–QH, QH' | NC (QD was `LED_OE_N` in Rev A) |

Protocol: drive `SEL_OE_N` high, shift the select byte, pulse `SEL_LAT`, drive `SEL_OE_N` low for the transaction, and return to all-inactive before changing targets. Never enable outputs with more than one CS low, and never shift a latch byte while an IMU CS is enabled. Shift 1s into unused bits.

---

## AM32 ESC

`J4` (JST-GH 4-pin):

| Pin | Signal |
|---:|---|
| 1 | GND |
| 2 | `DSHOT1` (XIAO D4 via `R12` 33 Ω, clamp `D3`) |
| 3 | `DSHOT2` (XIAO D5 via `R13` 33 Ω, clamp `D4`) |
| 4 | GND |

Battery power reaches the ESC through `J1` (VBUS, GND), not through `J4`. Use DSHOT600 bidirectional with EDT; DSHOT300 only for bench work. Set the AM32 pole count correctly (pole pairs = poles / 2).

---

## ELRS receiver (off-board, S pocket)

**Receiver:** BetaFPV ELRS Lite 2.4 GHz, flat antenna V1.2 (ESP8285, CRSF, 5 V in, 11 × 10 × 3 mm). It lives in the S pocket with its antenna pointing outward, clear of the battery.

`J5` (JST-GH 4-pin):

| Pin | Signal | Direction |
|---:|---|---|
| 1 | GND | |
| 2 | 5V | Carrier buck to receiver |
| 3 | `CRSF_RX` | Receiver TX → XIAO D7 / GPIO1 (clamp `D5`) |
| 4 | `CRSF_TX` | XIAO D6 / GPIO0 → receiver RX (clamp `D6`) |

The Rev A KiCad footprint had the receiver pads in the order CRSF_TX, CRSF_RX, 5V, GND, which disagreed with the old spec table. Rev B defines the harness by `J5` alone; build the pigtail to the table above and check it against the receiver's silkscreen before soldering. Keep the harness short (under 60 mm) and twist the signal pair with GND. CRSF is non-inverted 420 kbaud UART; no inverter is needed.

---

## Battery voltage sense

`R9` 120 kΩ from VBUS, `R10` 33.2 kΩ to GND, `C12` 100 nF filter, to XIAO A0. About 2.47 V at 11.4 V nominal and 2.83 V at 13.05 V full charge (3S HV), inside the 3.3 V ADC range. Test pad `TP10`.

---

## Heading and status LED

Two orange TinySLED modules in parallel, one visible from the top, one from the bottom, on `J2` (JST-GH 2-pin; pin 1 VBUS, pin 2 `HEAD_SW`) through a Y-spliced harness. `Q1` AO3402 switches the return, driven from XIAO D1 through `R16` 100 Ω, held off by `R17` 100 kΩ.

At 4000 rpm one revolution is 15 ms and one degree is about 41.7 µs. Start with 300–500 µs strobes, phase-locked to heading. The strobe must be a hardware-timed one-shot with a hard maximum on-time, so a firmware hang cannot leave the LEDs on.

With the SK9822s gone, the TinySLED also carries status when the robot is not spinning:

| State | Pattern (robot stationary) |
|---|---|
| Boot / no RC link | 1 short blink every 2 s |
| RC link, disarmed | Solid 50 ms flash at 1 Hz |
| Armed, idle | Double blink at 1 Hz |
| Low battery | Fast 5 Hz blink |
| RC failsafe | Triple blink, pause |
| IMU fault | Long 1 s on, 1 s off |

Keep every on-time under the module's thermal limit (cap duty below about 25%).

---

## Debug edge

| Pad | Signal |
|---|---|
| `TP13` | SWDIO |
| `TP14` | SWDCK |
| `TP15` | GND |
| `TP10` | VBAT_SNS |
| UART | `CRSF_TX`, `CRSF_RX` (add 1 mm pads on these nets during layout; they double as a bench UART when the receiver is unplugged) |
| VBUS | Add a 1 mm VBUS probe pad during layout |

All of these are flush pads on the **bottom** copper, so they are reachable with the bottom plate off (see [Debug access](#debug-access)).

---

## Pin assignment

| XIAO pad | Signal | Notes |
|---|---|---|
| D0 / A0 | `VBAT_SNS` | Battery divider |
| D1 / A1 | `HEAD_LED` | TinySLED MOSFET gate |
| D2 / A2 | `SEL_OE_N` | Latch output enable |
| D3 / A3 | `SEL_LAT` | Latch clock |
| D4 | `DS1_IO` | AM32 ch 1 |
| D5 | `DS2_IO` | AM32 ch 2 |
| D6 / TX | `CRSF_TX` | To receiver |
| D7 / RX | `CRSF_RX` | From receiver |
| D8 / SCK | `SPI_SCK` | |
| D9 / MISO | `SPI_MISO` | IMU data in |
| D10 / MOSI | `SPI_MOSI` | IMUs and latch |
| SWDIO / SWDCLK | SWD | Test pads |
| 5V | 5V | From buck |
| 3V3 | 3V3 | To IMUs and latch |

---

## Harness

| Run | Connector | Wire |
|---|---|---|
| Battery to `J6` | XT30 female on battery | Pack leads |
| Switch pigtail to `J7` | XT30 male on pigtail | 20 AWG, as short as the frame socket allows |
| `J1` to ESC battery pads | Lap-soldered both ends | 20 AWG; routed off the ESC pads, along the S-ledge top, down the ledge face onto `J1` |
| ESC to each motor | MR30 on each motor's phases | Motor leads |
| `J4` to ESC signal | JST-GH 4-pin | 28 AWG |
| `J5` to receiver | JST-GH 4-pin | 28 AWG, twisted |
| `J2` to both TinySLEDs | JST-GH 2-pin, Y-splice near the plug | 26–28 AWG |

Zip-tie every lead through its strain-relief slot.

---

## Fabrication

| Item | Value |
|---|---|
| Layers | 2 |
| Thickness | 1.6 mm |
| Copper | 2 oz both layers |
| Finish | ENIG |
| Min trace / space | 0.15 / 0.15 mm (2 oz makes 0.1 mm impractical; check the LGA fanout) |
| Assembly | Paste and reflow or hot air for the LGAs |
| Stencil | Stainless, ordered with the board |

---

## Open items

1. **Outline and layout.** The routed `guac.kicad_pcb` is still the Rev A layout. Update the PCB from the schematic, import `cad/rev2/board_outline.dxf` to Edge.Cuts, and re-place against `cad/rev2/keepout.dxf`.
2. **Chassis v34 (done).** Ledge recesses, M2 heat-set bores, mirrored groove, new bottom plate with wafer-head holes and THT reliefs, and shelf windows over `J6` (SE shelf ends at y −15.1) and `J7` (NW gap y 21.8…29.0). Keep both XT30s inside those windows.
3. **Buck light-load check.** Scope the 5 V ripple at the real ~120 mA load to confirm the AP63301 choice.
4. **Rev A bodge.** On existing Rev A boards, lift or cut R6/R7/R8 pin 2 from MOSI and jumper them to D9 before IMU bring-up.
5. **Receiver pinout.** Confirm the physical receiver pads before building the `J5` pigtail.
6. **TinySLED at 13.05 V.** The module is sold as 2–3S, which likely means 12.6 V max. Melty Discord users report Tiny's LEDs use a series resistor and no regulation, so current rises with pack voltage; 13.05 V is about 3.5% over 12.6 V, which pushes LED current up more than that. Either confirm with Tiny's, or use the 3–6S version (tinysleds.com/products/3-6s-led), which has full margin at 13.05 V at the cost of some brightness. Q1 (AO3402, 30 V) is fine either way.
7. **TinySLED status codes.** Implement and check thermal behaviour at the chosen duty.
8. **Through-hole pins vs bottom plate.** Only `J6` and `J7` are through-hole now (4 pins). The bottom plate has Ø4 reliefs at their pins; trim the tails flush. The two `J1` reliefs can go.
9. **Tall parts vs battery.** `L1` (6 mm) must stay outside the battery strip (limit 4.7 mm); `C21` is now ≤ 4.3 mm.
10. **IMU coordinates.** Measure after assembly and store in firmware.
11. **Power integrity.** Scope VBUS, 5V, and 3V3 during spin-up, regen braking, and TinySLED strobes.

### Later

Put the dual AM32 ESC on the carrier itself (4-layer). This removes the separate ESC, its harness, and about 6 g, but it is a large project; not before Buckeye Bash.
