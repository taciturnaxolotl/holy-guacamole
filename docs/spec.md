# Holy Guacamole: System and Carrier PCB Specification

**Document status:** Rev B 2.1, regenerated 2026-11-10 against repo commit `96137c3` ("reroute pcb to fit pcbway reqs") and chassis v3.4f. The KiCad schematic `hardware/guac.kicad_sch` and board `hardware/guac.kicad_pcb` are the source of truth for the electronics. `concept_v33.py` (v3.4f) is the source of truth for the chassis. `hardware/circuit.py` is a stale SKiDL sketch and no longer matches either.
**Robot:** Holy Guacamole, 1 lb meltybrain antweight, MRCA full combat.
**Previous revisions:** Rev A (v1.3c: 40 × 50 mm board, fly-lead pads, solder-down receiver) and Rev B 2.0-draft (pre-route). See git history for that text.

---

## System summary

| Item | Value |
|---|---|
| Mass | 446 g by CAD (limit 454). Allow +1–3% for MJF density, so about 450–459 g worst case. 2.4 g of trim at r44 balances the CoM |
| Size | Ø145 × 29 mm frame; Ø180 over the two teeth |
| Frame | Two MJF PA11 halves, split at the ring top (z 16.9). Made by an outside manufacturer |
| Weapon ring | AR550 3/16" (4.76 mm), Ri 73 / Ro 78, two teeth, 126 g. Clamped by 6 × Ti M3 × 20 button-head screws with Ø7 washers into M3 × 5.7 brass heat-sets in the upper half, 0.3 N·m |
| Ring liners | TPU, printed at home, one U-liner per ear. Three fits are provided (ear clearance 0.30 / 0.15 / 0.05 mm). Use the snuggest set that slides on, so the ear bears on the liner before the bolts |
| Plates | Top and bottom, MJF PA11 0.8 mm, 4 × M2.5 each, in 0.6 mm pockets |
| Drive | 2 × Palm Beach Bots D2822 1100KV, 1/8" shaft, 70 mm leads to 2 mm bullets |
| Wheels | Ø42 × 9 mm: PA11 hub with a cast VytaFlex 40 tread (printed moulds), outboard MR128 bearing (seat reamed to 12 mm) |
| Battery | GNB 3S 380 mAh HV, 55 × 17 × 20 mm, 32 g, 13.05 V full |
| ESC | Repeat AM32 dual, 28 × 20 mm, standing on edge against the S bay wall. Current limit 4–5 A per channel |
| Receiver | BetaFPV ELRS Lite flat-antenna, on a tray in the S pocket, wired to `J5` |
| Heading LEDs | 2 × orange TinySLED (top and bottom) on `J2` through a Y-splice |
| Controller | Seeed XIAO RP2350 on the Rev B carrier (this document) |

### Chassis verification (v3.4f)

- Every assembly, service, and tool-access check clears, with no trapped cavities. A fit audit checked every part against MJF's ±0.3 mm tolerance; the v3.4f tolerance pass opened every unintended tight face.
- Static FEA of an 11 kN tooth hit: 33.6 MPa with the bolts only and 30.1 MPa with the ring supporting, both peaking at the same spot near (47, 25, 22). That is a factor of safety of 1.55 against 52 MPa.
- Lowest free-free mode is 286 Hz (battery ribs). There is no frame-against-ring mode below 951 Hz. Wheel-rev excitation is 200 Hz at 4500 rpm.
- Skin poke: a 300 N load on a 6 mm patch first yields at 50–90 N. Skin gussets did not help and were not adopted.
- Heat-set pull-out is marginal under a large vertical hit.

---

## What changed from Rev A

| # | Change | Why |
|---|---|---|
| 1 | The carrier is now the power distribution board. The battery and switch loop land on vertical XT30s, and the ESC battery feed leaves from 20 AWG SMD lap pads at the S edge. | Removes the J1 pigtail, the 16 AWG splices, and the separate PDB. This deliberately reverses the Rev A rule that high current never touches the carrier. |
| 2 | Latching JST-GH connectors for the ESC signal, the receiver, and both TinySLEDs. | Solder pads and fly-leads were the weakest joints in impacts. |
| 3 | The ELRS receiver moves off-board to the S pocket on a JST-GH harness. `U7` is gone; `J5` replaces it, with ESD clamps `D5`/`D6`. | Gets the antenna out of the battery's shadow and off the board's copper. |
| 4 | 100 µF / 25 V polymer tantalum bulk capacitor `C21` on VBUS near the ESC feed. | Absorbs ESC regen and hot-plug ringing on the board-mounted bus. |
| 5 | SK9822 status-LED chain deleted (`U8`, `U9`, `U10`, `U12`, `C14`–`C17`, `R14`, `R15`, `R21`). `U11` QD is NC. | Neither LED has a window in the chassis; the TinySLED blinks status codes instead. |
| 6 | The MCP23S17 expander is replaced by an SN74HC595 chip-select latch (`U11`). | Simpler; three CS lines are all that is needed. |
| 7 | Duplicate CS pull-ups `R19`/`R20` deleted. | `R4`/`R5` already do the job. |
| 8 | **Bug fix:** `R6`/`R7`/`R8` (IMU SDO series resistors) now land on `SPI_MISO`. In Rev A they were wired to `SPI_MOSI` in both schematic and PCB. | Rev A boards cannot read the IMUs without a bodge (see Open items). |
| 9 | New 40 × 76 mm outline centred on the spin axis, ends clamped under the chassis end ledges. 4 layers, 1.6 mm, 2 oz outer copper, 4 × M2 screws. | See [Board outline](#board-outline-and-mechanical). |
| 10 | 3S HV is now the design pack; 2S stays selectable on `JP1`. | More spin-up torque without a board respin. |
| 11 | The ESC BEC stays isolated, as in Rev A. | Unchanged policy. |

Review suggestions that were **not** taken as written:

- **TVS at the battery entry.** `D2` stays on VBUS (the switched side). The large transients come from the ESC (regen braking), and those land on VBUS. With the switch open, the carrier is unpowered and needs no clamp.
- **Bottom TinySLED connector on the underside.** The board sits 0.32 mm above the bottom plate, so nothing can go on the underside. Both LEDs share `J2` on the top side through a Y-splice, so `J3` is gone.
- **Foam under the board.** The bottom plate is recessed to 0.32 mm below the board. No foam; flush pads only.

---

## Overview

The carrier hosts a Seeed XIAO RP2350 module. The XIAO provides the RP2350, flash, USB, crystal, and the 3.3 V regulator. The carrier provides:

- Battery, switch-loop, and ESC power distribution on board copper.
- A 5 V buck rail from the switched LiPo bus (3S HV design pack; 2S supported through the UVLO jumper).
- SPI to one inner LSM6DSV320X 6-axis IMU and two outer H3LIS331DL high-G accelerometers. Their chip-selects come from an SN74HC595 latch loaded over the same SPI bus.
- Two direct bidirectional DSHOT/EDT lines to the Repeat AM32 dual ESC.
- A CRSF UART and 5 V feed to the off-board ELRS receiver.
- Independent battery voltage sensing.
- A low-side MOSFET driver for the two paralleled TinySLED heading LEDs.
- Flush debug pads on the underside: SWD, UART, VBAT, and GND.

Runtime IO stays on the XIAO edge pads. The XIAO's underside pads are NC.

---

## Reference designators

| Ref | Function | Footprint |
|---|---|---|
| `U1` | Seeed XIAO RP2350 SMD module (hand-soldered; not placed by assembly) | `Library:XIAO-RP2350-SMD` |
| `U2` | AP63301WU-7 3 A synchronous buck, 5.0 V via divider | TSOT-23-6 |
| `U4` | LSM6DSV320XTR inner IMU | LGA-14 |
| `U5`, `U6` | H3LIS331DLTR outer high-G accelerometers | LGA-16 3 × 3 |
| `U11` | SN74HC595PWR chip-select latch | TSSOP-16 |
| `Q1` | AO3402 TinySLED low-side switch | SOT-23 |
| `J1` | ESC battery feed: two 2.6 × 4.0 mm SMD lap pads for 20 AWG. Pad 1 VBUS on the E (board-edge) side, pad 2 GND on the W side | `SolderLap_20AWG_1x02_2.6x4.0mm_P3.2mm` (project library) |
| `J2` | TinySLEDs, JST-GH 2-pin | `JST_GH_SM02B-GHS-TB` |
| `J4` | AM32 ESC signal, JST-GH 4-pin | `JST_GH_SM04B-GHS-TB` |
| `J5` | ELRS receiver harness, JST-GH 4-pin | `JST_GH_SM04B-GHS-TB` |
| `J6` | Battery, XT30 male, vertical | `AMASS_XT30UPB-M` |
| `J7` | Switch loop, XT30 female, vertical | `AMASS_XT30UPB-F` |
| `JP1` | UVLO select solder jumper (open / 2S / 3S) | 3-pad jumper |
| `L1` | 5.6 µH Bourns SRP6060FA | SRP6060FA |
| `C21` | 100 µF 25 V polymer tantalum, ≤ 4.3 mm tall | `CP_EIA-7343-43_Kemet-X` |
| `D2` | SMAJ15CA bidirectional TVS on VBUS | SMA |
| `D3`, `D4` | ESD clamps on DSHOT1/DSHOT2 at `J4` | SOD-523 |
| `D5`, `D6` | ESD clamps (ESD5B5.0ST1G) on CRSF_RX/CRSF_TX at `J5` | SOD-523 |
| `TP10`, `TP13`–`TP15` | VBAT_SNS, SWDIO, SWDCK, GND test pads | 1 mm pad |

Free refs from deletions: `R14`, `R15`, `R19`, `R20`, `R21`, `C14`–`C17`, `U7`–`U10`, `U12`, `J3`. Do not reuse them in this revision, so old BOMs and photos stay unambiguous.

### Buck part choice

The board uses the **AP63301WU-7** (forced PWM). It shares a datasheet ([Diodes AP63300/AP63301](https://www.diodes.com/datasheet/download/AP63300_AP63301.pdf)), pinout, 0.8 V ±1% reference, 500 kHz clock, and EN thresholds (1.18 V rising, 1.09 V falling) with the AP63300. The two parts differ only at light load:

| | AP63300 | AP63301 |
|---|---|---|
| Light-load mode | PFM bursts, 930 mA peak inductor current | PWM at every load |
| Switching frequency | Spread-spectrum PWM; variable in PFM | Fixed 500 kHz |
| Quiescent current | 22 µA | 280 µA |

The 5 V load is about 100–150 mA (XIAO plus receiver), which would keep an AP63300 in PFM. Its 930 mA bursts at an irregular rate would sit next to three accelerometers, the VBAT ADC, and the CRSF line. A fixed 500 kHz is easier to filter and to recognise on a scope. The extra 0.26 mA costs about 0.07% of the pack per hour.

---

## Power architecture

```text
3S HV LiPo, 9.0–13.05 V
  -> J6 XT30-M (battery, SE corridor)        net VBAT_RAW
      -> J7 XT30-F (switch loop, NW corridor) pin 2 VBAT_RAW out
          -> Fingertech switch on a short XT30 pigtail, in its frame socket
      <- J7 pin 1                              net VBUS (switched)
          -> C21 100 µF bulk + D2 SMAJ15CA     at the S edge
          -> J1 pads -> AM32 dual ESC battery pads (20 AWG)
          -> U2 buck -> 5V
                -> XIAO 5V pad -> XIAO 3V3 -> IMUs, latch, pull-ups
                -> J5 pin 2 -> ELRS receiver
          -> R9/R10 divider -> VBAT_SNS (XIAO A0)
          -> J2 pin 1 -> both TinySLEDs -> Q1 -> GND
```

`J6` and `J7` polarity follows the AMASS footprint marks: pad 1 is the "−" side, pad 2 the "+" side.

- `J6`: pad 1 GND, pad 2 VBAT_RAW.
- `J7` carries no ground: pad 1 is VBUS (the switch return), pad 2 is VBAT_RAW. **Silkscreen `J7` as "SW" with both pads labelled, not "+/−"**, so nobody plugs a battery into it.

Gender convention: the battery lead carries the female XT30, so the board gets the male (`J6`). The switch-loop socket is live from the battery, so its board side is female (`J7`) and the switch pigtail is male.

### Copper and current

| Item | Rule |
|---|---|
| Copper weight | 2 oz outer, 1 oz inner |
| Current | Up to about 16 A on VBUS/GND at 4–8 A per ESC channel, sustained for the whole match (a meltybrain spins continuously). The AM32 limit is set to 4–5 A per channel |
| VBAT_RAW, VBUS | Sized for sustained current. Every stretch is about 4 mm or more on one outer layer, or doubled on a second layer, with one exception: 10 mm of VBUS beside `J6` is 2.54 mm on F.Cu alone, where `J6` pin 2 takes In2 and B.Cu. About 9 mΩ of board copper end to end, counting In2 as 1 oz (8.4 mΩ measured before the PCBWay reroute; the reroute trimmed the B.Cu VBAT_RAW pour by about 13%, so re-measure) |
| VBUS to VBAT_RAW | 1.0 mm minimum on the outer layers (`guac.kicad_dru`). Both strips face the bottom plate, and a metal chip bridging them shorts the switch. 0.5 mm on In2 |
| Inner layers | In1 is solid GND. In2 carries 3V3 (centre), 5V (W edge, N end, and a finger to `J5`), and E-edge VBUS and VBAT_RAW strips that double the outer power copper |
| GND | Poured on all layers and stitched. The high-current return from `J1` to `J6` does not run under the IMU array |
| Via stitching | At least six vias of 0.4 mm drill or larger at every power-path layer change |

The buck input caps (`C1`, `C19`, `C20`, `C2`) take VBUS from the pour, not from the ESC path. The ESC current loop (`J6` → `J7` → `J1` and back) runs along the board's E edge strip, away from `U4`–`U6` and the `VBAT_SNS` divider.

### ESC BEC policy

The Repeat AM32 BEC stays **isolated**; do not tie it to the carrier 5 V rail. This keeps a known 5 V source on the controller, keeps the controller up if the ESC resets, and keeps BEC noise out of the IMU domain. Revisit only after scoping BEC voltage and noise under motor load.

### Buck regulator

| Parameter | Value |
|---|---|
| Part | AP63301WU-7, TSOT-23-6 |
| Input | 3.8–32 V part rating. Design range is VBUS 9.0–13.05 V (3S HV); 2S (6.0–8.4 V) also works |
| Output | 5.0 V, set by `R27` 158 kΩ / `R28` 30.1 kΩ, with `C18` 47 pF feed-forward |
| Inductor | `L1` 5.6 µH Bourns SRP6060FA |
| Input caps | `C1`, `C19`, `C20` 22 µF 25 V 0805 + `C2` 100 nF |
| Output caps | `C4`, `C5` 22 µF |
| Bootstrap | `C3` 100 nF |
| UVLO | `JP1` selects the divider. **Bridge 2-3 for this pack** = 3S: `R25` 75 kΩ / `R26` 10 kΩ, about 8.85 V off / 9.92 V on (2.95 V/cell). Bridge 1-2 = 2S: `R23` 47 kΩ / `R24` 10 kΩ, 5.96 / 6.66 V. Leave open to bypass |
| Input-cap margin | At 13.05 V each Samsung `CL21A226MAYNNNE` keeps a little under 4.4 µF, so the three-cap worst case is about 10 µF, right at the reference design value. For more margin, use a 35 V 22 µF 0805 such as Murata GRM21BR6YA226ME43 |

On the routed board, `C2` (100 nF) then `C1` sit directly off U2 VIN/GND, with a loop under 3 mm. `C19`/`C20` sit beside `C1` on a 0.6 mm VBUS spine that drops into the N VBUS strip. FB is taken from the `C4`/`C5` node. `L1` and the SW node are kept away from the IMUs and `VBAT_SNS`. `L1` is the tallest part after the XT30s; stake it (see [Impact hardening](#impact-hardening)).

---

## Board outline and mechanical

The outline and keepouts come from the chassis and live in `cad/rev2/` (`board_outline.dxf`, `keepout.dxf`, `README.md`). If this section and `cad/rev2/README.md` disagree, the README wins. Placement has not moved since `244dd04`, so chassis v3.4f fits the `96137c3` board unchanged.

| Parameter | Value |
|---|---|
| Outline | 40.0 × 76.0 mm, x −20…+20, y −38…+38, corner R1.5, centred on the spin axis. A USB notch in the N edge runs x 0.4…13.0 from y 29.2 |
| Origin | Spin axis; +Y points N. In KiCad coordinates, kx = 80 + x and ky = 65.5 − y |
| Thickness | 1.6 mm FR4 |
| Mounting | 4 × M2 into 3 mm heat-sets in the end-ledge undersides, at (±16.6, +34.5) and (±17.0, −34.5). 2.2 mm drill, 4.5 mm keepout |
| Board bottom | z 0.9 |
| Underside | Only flush bottom-copper test pads, nothing taller than solder mask. The gap to the bottom plate is 0.32 mm; no foam |
| Layers | 4 |
| Finish | ENIG (the LGA pads need flat pads) |

### Chassis features for the board (in v3.4f)

1. A recess in the underside of each end ledge: x ±20.5, |y| 29.9…38.5. The board drops in from below.
2. Four M2 heat-set bores (≤ 3.7 mm deep with a 1.6 mm board).
3. Bottom plate: 5 mm through-holes for the M2 heads, and Ø4 reliefs under the `J6`/`J7` pins.
4. S-ledge wire groove at x −4.5…+13.5. The ESC stands with its BAT/GND corner on the E side.
5. Shelf windows over `J6` (the SE shelf ends at y −15.1) and `J7` (the NW gap runs y 21.8…29.0).

### Z budget

The board bottom is at z 0.9. The bottom plate (0.8 mm) tops out at z 0.58, in a 0.6 mm pocket. The ledge and battery floor are at z 7.2. The battery sits at x ±8.5, y −23.2…+31.6, with its leads and XH balance plug leaving the S end, so it covers a 17 mm strip of the board. A cross-beam under its S end (y −24.8…−19.8, z 4.0…7.2) limits parts there to 1.2 mm.

| With a 1.6 mm board | Value |
|---|---:|
| Board top | z 2.50 |
| Max part height under the battery | 4.70 mm |
| XIAO + USB-C margin to the battery floor (the part still under the pack) | 0.40 mm |
| Max part height in the motor-screw key band | 4.03 mm |
| Gap to the bottom plate | 0.32 mm |

| Region | Height limit above the board |
|---|---|
| Battery strip, \|x\| ≤ 6.5 | 4.7 mm |
| Side corridors, \|x\| 6.5…20.5 | about 23 mm (open to the rib shelves at z 25.5) |
| Motor-screw key band, \|y\| ≤ 8, in the corridors | about 4 mm |
| Motor-lead entries, y −25…−15, z 9.8…19.2 | about 7 mm |
| Ledge-clamped ends, \|y\| ≥ 29.9 | none (no top-side parts) |

`L1` (6 mm) sits in the NW corridor. `C21` (≤ 4.3 mm) fits in the battery strip in the S, about 12 mm from `J1`. A 25 V polymer part at 13.05 V runs at 52% of its rating, inside the usual 80% derating. A mated XT30 stands about 21 mm, topping out near z 23.5 under the 26.5 side shelves; route its 16 AWG off sideways.

USB runs through a ribbon extension with a slim male end, from the XIAO to a USB-C female on the shelves (z 19.4…21.4) under the top-plate slot.

### Placement

Exact coordinates are in `cad/rev2/README.md`.

| Region | Contents |
|---|---|
| NE corridor | XIAO, as far into the corridor as its 17.5 mm width allows, with its USB-C end in the plug channel (x 0.7…12.7) under the N ledge |
| NW corridor | `L1` (y 11…18) and `J7`, the switch-loop XT30, near the switch at (−5, 50.5) |
| SE corridor, above the ESC pads | `J6` battery XT30, clear of the key band and the motor-lead entries |
| SE key band | `D2` |
| Battery strip, S | `C21` |
| S gap, SE | `J1` ESC power lap pads (south of the beam) and `J4` ESC signal. The ESC stands against the S bay wall with BAT/GND on the E side; its leads drop through the groove |
| W corridor, north of the beam | `J2` TinySLED socket at (−14.0, −16.3), opening N, with the plug and Y-splice north of it under the L-key sweep. The LED leads come up from the SW channel mouth (keep it clear) |
| S, near x 0 | `J5` receiver harness; the leads come down beside the ESC into the groove |
| Centre | IMU array around the spin axis |
| \|y\| > 29.9 | Nothing on top (clamped under the ledges) |

### Debug access

With the bottom plate off, only the underside and the four screws can be reached. The E and W edges sit 0.5 mm from the walls and the ends are under the ledges. So the debug pads (`TP13` SWDIO, `TP14` SWDCK, `TP15` GND, `TP10` VBAT_SNS, plus pads on `CRSF_TX`/`CRSF_RX` and VBUS) are **flush, unpopulated pads on the bottom copper**, the one exception to "nothing on the underside". USB through the chimney works with the top plate off and the battery in.

### IMU placement

The nominal array is U4 at 0°/r12, U5 at 90°/r18, U6 at 210°/r18 (the asymmetry breaks heading singularities). Nominally that puts U5 under the XIAO. Rotating the **whole array 166° CCW** clears everything; only 164–168° works.

| Sensor | Nominal | As placed (+166°) | Board position (x, y) | Accel at 4000 rpm |
|---|---|---|---|---:|
| `U4` LSM6DSV320X | 0°, r12 | 166° | (−11.64, 2.90) | about 216 g |
| `U5` H3LIS331DL | 90°, r18 | 256° | (−4.35, −17.47) | about 324 g |
| `U6` H3LIS331DL | 210°, r18 | 16° | (17.30, 4.96) | about 324 g |

Sensor axis map from the footprint rotations: the radial-outward direction is **+X on U4, +Y on U5, and −X on U6**. Firmware must take this per-chip mapping instead of assuming X radial on every chip. Store **measured** post-assembly IMU coordinates in firmware.

The 166° window depends on `J2`, `J6` and `C21`; moving any of them can close it, so re-check after any change.

---

## Impact hardening

1. 1.6 mm board on four mounting points.
2. No MLCC within 2 mm of a mounting hole or 1 mm of an edge. Orient 0805 caps parallel to the nearest edge. Use soft-termination parts for `C1`, `C19`, `C20`, `C4`, `C5` where available (for example Murata GCJ or KEMET FT-CAP).
3. Stake `L1`, `C21`, and the XIAO corners with epoxy after the electrical test.
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
| `SPI_MISO` | D9 / GPIO4 | IMU data return |
| `CS_A` / `CS_B` / `CS_C` | `U11` QA / QB / QC | Pulled up by `R11` / `R4` / `R5` 10 kΩ |

Decoupling: `C8` and `C11` (U4 VDD and VDDIO), `C9` (U5), and `C10` (U6), each 100 nF, plus `C6` and `C13` 10 µF near the outer sensors. On the routed board `C9` and `C10` sit about 3.7 mm from their chips.

Firmware selects one IMU at a time. A three-IMU read set takes about 15–30 µs at 10 MHz, about 0.7° of skew at 4000 rpm, which firmware compensates.

### H3LIS331DL shared-bus I2C exposure

The H3LIS331DL has no I2C-disable bit. With its CS high, it listens to `SPI_SCK`/`SPI_MOSI` as SCL/SDA. The bus therefore runs **SPI Mode 0** (SCK idles low). In Mode 0, SDA only changes while SCL is low, so an I2C START can never form. `R22` holds SCK low through boot and reset, and firmware must keep SCK low at idle (this is automatic with the PL022; with PIO it must be explicit). Do not use Mode 3. Firmware also sets the LSM6DSV320X `IF_CFG.I2C_DISABLE` bit and periodically reads back the H3LIS config registers.

H3LIS firmware notes: set BDU=1 (CTRL_REG4 bit 7), and use 0xE8 for multi-byte burst reads (RW=1 and MS=1).

---

## Chip-select latch (`U11` SN74HC595)

| Function | Signal |
|---|---|
| `/OE` | `SEL_OE_N`, XIAO D2, pulled up by `R1` 10 kΩ |
| `RCLK` | `SEL_LAT`, XIAO D3, pulled down by `R18` 100 kΩ |
| `SER` | `SPI_MOSI` |
| `SRCLK` | `SPI_SCK` |
| QA / QB / QC | `CS_A` / `CS_B` / `CS_C` |
| QD–QH, QH' | NC |

Protocol:

1. Drive `SEL_OE_N` high.
2. Shift the select byte, with 1s in the unused bits.
3. Pulse `SEL_LAT`.
4. Drive `SEL_OE_N` low for the transaction.
5. Return to all-inactive before changing targets.

Never enable the outputs with more than one CS low, and never shift a latch byte while an IMU CS is enabled.

---

## AM32 ESC

`J4` (JST-GH 4-pin):

| Pin | Signal | Harness colour |
|---:|---|---|
| 1 | GND | |
| 2 | `DSHOT1` (XIAO D4 via `R12` 33 Ω, clamp `D3`) | white |
| 3 | `DSHOT2` (XIAO D5 via `R13` 33 Ω, clamp `D4`) | yellow |
| 4 | GND | |

Battery power reaches the ESC through `J1` (VBUS, GND), not through `J4`. Use DSHOT600 bidirectional with EDT; DSHOT300 is for bench work only, since bidirectional mode halves the effective command rate. Set the AM32 pole count correctly (pole pairs = poles / 2). Firmware profile: `AM32_RR_ROBOT_DUAL_ESC_F421`.

---

## ELRS receiver (off-board, S pocket)

**Receiver:** BetaFPV ELRS Lite 2.4 GHz, flat antenna V1.2 (ESP8285, CRSF, 5 V in, 11 × 10 × 3 mm). It sits on a tray in the S pocket with its antenna pointing outward, clear of the battery.

`J5` (JST-GH 4-pin):

| Pin | Signal | Direction |
|---:|---|---|
| 1 | GND | |
| 2 | 5V | Carrier buck to receiver |
| 3 | `CRSF_RX` | Receiver TX → XIAO D7 / GPIO1 (clamp `D5`) |
| 4 | `CRSF_TX` | XIAO D6 / GPIO0 → receiver RX (clamp `D6`) |

Build the pigtail to this table and check it against the receiver's silkscreen before soldering. Keep the harness under 60 mm and twist the signal pair with GND. CRSF is a non-inverted 420 kbaud UART, so no inverter is needed.

---

## Battery voltage sense

`R9` 120 kΩ from VBUS and `R10` 33.2 kΩ to GND, with a `C12` 100 nF filter, into XIAO A0. That gives about 2.47 V at 11.4 V nominal and 2.83 V at 13.05 V full charge, inside the 3.3 V ADC range. Test pad `TP10`.

---

## Heading and status LED

Two orange TinySLED modules run in parallel, one visible from the top and one from the bottom. They connect to `J2` (JST-GH 2-pin: pin 1 VBUS, pin 2 `HEAD_SW`) through a Y-spliced harness. `Q1` AO3402 switches the return, driven from XIAO D1 through `R16` 100 Ω and held off by `R17` 100 kΩ.

At 4000 rpm one revolution takes 15 ms and one degree about 41.7 µs. Start with 300–500 µs strobes, phase-locked to heading. The strobe must be a hardware-timed one-shot with a hard maximum on-time, so a firmware hang cannot leave the LEDs on.

When the robot is not spinning, the TinySLED also shows status:

| State | Pattern (robot stationary) |
|---|---|
| Boot / no RC link | 1 short blink every 2 s |
| RC link, disarmed | Solid 50 ms flash at 1 Hz |
| Armed, idle | Double blink at 1 Hz |
| Low battery | Fast 5 Hz blink |
| RC failsafe | Triple blink, pause |
| IMU fault | Long 1 s on, 1 s off |

Keep duty below about 25% so on-times stay under the module's thermal limit.

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
| Battery to `J6` | XT30 female on the battery | Pack leads |
| Switch pigtail to `J7` | XT30 male on the pigtail | 20 AWG, as short as the frame socket allows |
| `J1` to ESC battery pads | Lap-soldered at both ends | 20 AWG. J1 red lands on the pad at x 18.2, black on the pad at x 15.0, each up its own wall channel |
| ESC to each motor | 2 mm bullets | Motor leads, about 70 mm |
| `J4` to ESC signal | JST-GH 4-pin | 28 AWG |
| `J5` to receiver | JST-GH 4-pin | 28 AWG, twisted |
| `J2` to both TinySLEDs | JST-GH 2-pin, Y-splice near the plug | 26–28 AWG |

Zip-tie every lead through its strain-relief slot.

---

## Fabrication (PCBWay)

| Item | Value |
|---|---|
| Fab | PCBWay (sponsor), normal process with no advanced options (pcbway.com/capabilities.html, Advanced PCB table) |
| Layers / thickness | 4 layers, 1.6 mm FR4 |
| Copper | 2 oz outer, 1 oz inner |
| Finish | ENIG |
| Mask / silk | Green / white |
| Vias | Tented |
| Quantity | 5 |
| Min trace / space | 0.18 / 0.21 mm (7 / 8 mil, the 2 oz outer-layer limit). Smallest routed track is 0.18 mm |
| Vias used | 0.62/0.25 (autorouted signal), 0.7/0.3, 0.75/0.35, and 0.8/0.4 mm. Smallest ring 0.185 mm (≥ the 7 mil, 0.178 mm, limit) |
| Plated component holes | 0.31 mm ring (12 mil on 2 oz) and 0.41 mm hole to hole |
| Inner layers | 0.18 mm hole-to-copper isolation (7 mil on 4 layers) |
| Rules | `guac.kicad_pro` and `guac.kicad_dru` hold these limits. KiCad DRC is clean against them |
| Assembly | Top side only. `U1` (XIAO) is not placed; it is hand-soldered. `J1` has no part (bare lap pads). The BOM comes from `scripts/pcbway_bom.py` |
| Stencil | Stainless, ordered with the board |

Independent check of `96137c3`: all 63 nets are connected, placement is identical to `244dd04`, and the outer VBUS↔VBAT_RAW gap is 1.0 mm.

---

## Open items

1. **`C21` part number.** The PCBWay BOM still lists it as TBD. Pick a real 100 µF / 25 V polymer tantalum in 7343-43 (≤ 4.3 mm). Two 47 µF in parallel are fine if 100 µF isn't stocked.
2. **3S UVLO cutoff.** `R25` 75 kΩ cuts at about 8.85 V (2.95 V/cell), which can trip under spin-up sag on a 380 mAh pack. Changing `R25` to 66.5 kΩ moves the cutoff to about 8.0 V. Decide before ordering.
3. **Pack capacity.** A 3-minute match at about 10 A average draws about 500 mAh, against 380 mAh. Either confirm the real average current with a bench soak, lower the ESC current limit, or move to a larger pack.
4. **Bench soak.** Run 3 minutes at the ESC current limit and check copper and connector temperature. Re-measure the power-path resistance after the reroute.
5. **TinySLED at 13.05 V.** The module is sold as 2–3S, which likely means 12.6 V max. Tiny's LEDs reportedly use a series resistor with no regulation, so 13.05 V pushes the current up by more than 3.5%. Either confirm with Tiny's or use the 3–6S version (tinysleds.com/products/3-6s-led). `Q1` (30 V) is fine either way.
6. **Buck light-load check.** Scope the 5 V ripple at the real ~120 mA load to confirm the AP63301 choice.
7. **Power integrity.** Scope VBUS, 5V, and 3V3 during spin-up, regen braking, and TinySLED strobes.
8. **IMU coordinates and axes.** Measure them after assembly and store them in firmware, using the per-chip axis map above.
9. **Receiver pinout.** Confirm the physical receiver pads before building the `J5` pigtail.
10. **TinySLED status codes.** Implement them and check thermal behaviour at the chosen duty.
11. **Through-hole tails.** Only `J6` and `J7` are through-hole (4 pins). Trim their tails flush over the Ø4 bottom-plate reliefs.
12. **Rev A bodge.** On existing Rev A boards, lift or cut R6/R7/R8 pin 2 from MOSI and jumper them to D9 before IMU bring-up.
13. **Firmware plant parameters.** Update them for 3S, the Ø42 wheel, and the v3.4f geometry.

### Later

Put the dual AM32 ESC on the carrier itself. That would remove the separate ESC, its harness, and about 6 g, but it is a large project.
