# holy guacamole v3.4h (2026-11-16): chassis + rev-2 carrier + harness

Units are mm. The spin axis is z, and the origin is the centre of the frame's bottom face. +y = N (switch / USB end), −y = S (ESC / receiver end), +x = E motor. Every file is in bot coordinates, so they all drop into one assembly without moving anything.

**Status:**
- **Mass:** 447 g (limit 454). Needs 2.9 g of balance trim at r44.
- **Fit:** every assembly, service and tool sweep passes, with no overlaps.
- **Printing:** 0 trapped-powder cavities, and both halves are one solid each.
- **FEA (`fea_v33.py`, 4000 rpm + impacts, allow 30 MPa):** ring-supported worst case FoS 1.03, same as v3.4g (1.00). The bearing end walls peak at 13.9 MPa (FoS 2.2). The bolts-only bound shows one 31.7–36.9 MPa node on the ring lip at the 150° ear; the next node down is 27.7 MPa, matching v3.4g, so it reads as a re-mesh spike, not a change from the wheels.
- **Harness:** collision-checked against the frame, the parts, the plug bodies and each other. The only contacts are deliberate: the ESC power leads have a 0.05 mm snap in the ledge channels, and the motor-lead strands touch where the twist starts.

**Board:** rev 2 placement with J7 beside J6 (since v3.4g). The PCB STEP is a placement reference: the board on `main` has since gained its silkscreen and ground fill, which change no outline or part position. The LED keepout layers get re-added board-side from `harness/harness.js`.

## Files
| path | what |
|---|---|
| `step/` | the parts one per file. **Print these in MJF PA11: `v33m_lower.step`, `v33m_upper.step`, `v33m_top.step`, `v33m_bot.step`** (plates 0.8 mm). The rest are reference bodies (motors, wheels, hubs, bearings, ring, TPU liners, battery, ESC envelope, PCB + parts, receiver, switch, LEDs, USB-C, XT30 courtyards) |
| `stl/` | viewer-only items: fasteners (Ti M3×20 ring bolts, M2.5×6 plate screws, M2×4 PCB screws, M3×6 motor screws, M2×5 wheel screws, brass inserts), detailed ESC, hex key, harness (one STL per circuit), plugs + 2 mm bullets + mated XT30s, foam/tape pads |
| `harness/` | `harness.js` (route source of truth), the sampler and the collision checker, sampled points |
| `viewer/holy-guacamole.html` | the offline 3D viewer: wiring view, section, explode, build animation (v3.4h). Rebuild it from `viewer/src/` |
| `renders/` | v3.4h stills: hero, exploded (labelled), drawing, section A-A, guts, wiring (+ SVG) |
| `ring/ring_fea.py` | the weapon ring's 2D geometry (`ring2d`, imported by `concept_v33.py`) and its tooth-hit FEA sweep |
| `scripts/` | generator + checks: cadquery → gmsh → CalculiX (`concept_v33.py topo_v33_0.12.npz mjf`, then `check`, `hw`, `printcheck`, `tools`, `fea`). `wheel_v33.py` builds the wheel (the hub, tread and bearing STEPs here, which the generator imports) and the tread mould STLs; the copies to order are in `../fab/wheel_mould`. The generator also needs the vendor STEPs `motor.step` (PBB D2822) and `switch.step` (Fingertech mini switch) in `../real/` (or `REAL=<dir>`); they are not in the repo |

## Z table
| z | what |
|---|---|
| −0.33…0.58 | bottom plate (0.91) in a 0.6 pocket (R63.5) |
| 0.9…2.5 | rev-2 carrier 40×76×1.6, up from below into the ledge recesses; 4× M2 into M2×3 heat-sets at (±16.6, +34.5), (±17.0, −34.5) |
| 0…7.2 | N and S end ledges (abs y ≥ 29.9); S-ledge wire groove x −4.5…13.5, z 2.7…7.3 |
| 7.2…27.2 | GNB 3S 380 HV pack 55×17×20 at x ±8.5, y −23.2…+31.6; 1.2 foam pad on top to the plate |
| 7.25…27.25 | Repeat AM32 dual ESC 28×20 on edge on the S ledge, FET side 0.8 off the S wall (y −38.7…−36.7) |
| 12.1…16.9 | AR550 ring; split plane = 16.9 |
| 16.9…29.0 | upper half. Battery ribs x ±8.75…10.75 (SE rib stops at y −19.2); L-shelves at z 25.5 with windows over J6 / J7 |
| 23.2…24.6 | receiver tray across the S pocket |
| 28.4…29.33 | top plate |

## What changed in v3.4h

The wheels go from 9 to **12 mm wide** (+33% tread), because narrow cast treads wear out fast on ant and beetle meltys (Discord: 9–10 mm T40s shredded in a fight; ~25 mm cast 40A lasted about 4).

| | v3.4g | v3.4h |
|---|---|---|
| wheel | Ø42 × 9, one dovetail + 12 ribs | **Ø42 × 12, two dovetails (at ⅓ and ⅔ width) + 12 ribs** |
| tread / hub | 3.6 g / 3.1 g | **5.0 g / 3.5 g** (pour 5.0 cc, ~6.5 cc with sprue) |
| wheel span | x 51.45…60.45 | **x 51.45…63.45** |
| MR128 bearing seat | x 60.6…64.1 | **x 63.6…67.1** (still Ø11.8 printed, ream to 12.0) |
| bearing end wall to the ring | 7 mm | **3.6 mm** (x 69.0…72.6); carries the ~250 N outward pull at 4000 rpm in compression, 13.9 MPa peak |
| wheel wells, plate notches, strut | follow the wheel (`WHEEL_W`), strut is 3 mm shorter |
| wheel centres | 111.9 apart | **114.9 apart** |

Unchanged: Ø42, the 6.5 mm the wheels stand proud of each face, motors, ring, board, harness. The viewer and renders are rebuilt for v3.4h.

## What changed in v3.4g

The switch-loop connector J7 moves from the NW corner to the SW corner, the mirror of the battery XT30 J6. The full ESC current used to go from J6 up the E edge and across the N end to J7 and back, passing 0.6 mm from U6 and under the XIAO (10.6 mΩ of board copper, ~1.1 W at 10 A). With J6 and J7 side by side it stays in the S end (target ~1.5–2 mΩ). The board work list is in `pcb-handoff-power.md` / the repo branch `chassis-v34g-j7-sw`.

| Change | Chassis | Board side (`cad/rev2/keepout.dxf`) |
|---|---|---|
| J7 XT30 to the SW | SW shelf window opens (y −19.2…−11, mirror of the SE one); the SW rib stops at y −19.2 like the SE rib | J7 pins (−13.8, −15.8) VBUS / (−13.8, −10.8) VBAT_RAW; bottom-plate reliefs follow |
| J2 (LEDs) to the old J7 spot, opens S | NW shelf window closes | J2 courtyard x −17.48…−10.52, y 23.0…29.4; plug y 18.5…23.0; Y-splice zone y 15.4…18.5 |
| L1 3 mm S | – | centre (−16.3, 11.55), y 8.0…15.1 |
| Switch pigtail | ~85 mm, twisted 20 AWG, N-stop notch → W corridor at z ≈ 24 (under the shelves, over the motor-screw key path) → J7 | – |
| LED leads | both leave the SW, run N along the W board edge at z 3.4–4.1, jog E N of U4, run N between L1 and the buck into the splice | `LED_LEADS_0P3` along the W edge |

Checks (v3.4g STEPs): mass 446 g CAD (limit 454), CoM trim 2.7 g at r44; assembly, service and tool sweeps all clear; 0 trapped cavities; harness: no new clashes (the two motor-bundle fan-ins and the J1 lead drop are the same as v3.4f); IMU rotation window 151…168°, 166° kept.

Structure: the SW window and rib stop are the exact mirror of the SE side, which is in the v3.4e FEA geometry (worst case 33.6 MPa, FoS 1.55, not at the ribs); closing the NW window only adds material. The FEA was not re-run for v3.4g.

## What changed in v3.4e
- **Edge:** the 45° ring lip is now an ogee. A concave R3 sweeps off the flank into a 0.5 mm flat at the tip, with the same 2.2 mm overlap on the ring. Skin under the R8 round is 1.0 mm (was 1.2). −2 g.
- **J2 opens N** (board `bbaf9d1`): the Y-splice runs N from the plug (x −14.0, y −8.3…−5.8, z 4.6). Both LED leads come up the W corridor; the bottom lead lies along the W board edge at x −19.4. U5 clearance is 9.8 mm.
- **J4 pin mapping:** 1 GND, 2 DSHOT1 (white), 3 DSHOT2 (yellow), 4 GND. EDT runs on the DSHOT lines.
- **Build animation** reordered to the physical assembly order.

## What changed in v3.4f

2026-11-10: the bearing strut in each upper-half wheel well now stops 0.3 mm inside the outer skin. It used to meet the skin with a 0.02 mm step (a 14 × 0.5 mm patch at x ±72, z 21–21.5) that showed as an edge in renders. No change to mass or strength.
Nothing in the halves now needs better than MJF's ±0.3 mm, except the bearing seats, which are sized to be reamed. The plates are now MJF PA11 instead of Tegris.

| fit | v3.4e | v3.4f |
|---|---|---|
| plates | Tegris 0.91, 8.9 g each | **MJF PA11 0.8, 9.4 g each**, printed with the halves (expect about 0.3–0.5 mm warp; the 4 screws pull them flat) |
| ring bore vs rim | 0.3 radial | **0.4** (sand the band if tight) |
| ring slot height | 4.763 + 0.3 | **measured ring + 0.3**: `RING_T_MEAS=<mm> python3 concept_v33.py …` |
| MR128 bearing seats | Ø12.1 | **Ø11.8 as printed, ream to 12.0** (shows as a 0.006 cc overlap in `check` on purpose) |
| ESC end walls / N lip | 0.3 / 0.2 | **0.4 / 0.4**, foam takes the slack |
| battery vs ribs / stops | 0.25 / 0.3 | **0.4 per side (ribs 1.85 thick, outer face unchanged) / 0.5** |
| switch socket | 0.2 | **0.4** + foam tape |
| plate pockets | R63.5 for the R63.3 plate, notches +0.2 | **R63.8, notches +0.5** |
| LED pockets | 0.3 | **0.4** |
| J1 lead channels | 1.5 (interference) | **1.9, 1.0 walls**: lay in, zip-tie or epoxy |
| USB-C board shelves | 1.5 deep (board missed them) | **2.6 deep**, 1.0 overlap each end |
| ring bolts | button head on the spot face | **Ø7 × 0.5 DIN 125 washer, Ø7.5 bottom spot face**, torque about 0.3 N·m |

- **Liners:** `liners/` has the TPU ear liners to print at home in three fits.

  | wall | ear clearance |
  |---|---|
  | 0.75 mm | 0.30 mm |
  | 0.90 mm | 0.15 mm |
  | 1.00 mm | 0.05 mm |

  Print a set of each and keep the snuggest set that still slides on.
- **Checks:**
  - **Mass:** 446 g with 2.7 g of trim. MJF parts usually come in 1–3% heavy, so plan for about 448–449 g.
  - **Assembly:** every step, service and tool sweep is clear.
  - **Print:** 0 trapped cavities.
  - **FEA (500 g impact + spin):** worst case is 33.6 MPa bolts-only, FoS 1.55 vs 52 MPa PA11.
  - **Harness:** clean.

## What changed in v3.4d
- **Rev-2 board fit:** XT30s turned 90°.
  - J6 pins are at (13.8, −15.8 / −10.8) and J7 pins at (−13.8, 21.8 / 26.8).
  - The SE shelf ends at y −19.2 and the NW shelf gap is y 18.6…30.0, so the mated plugs go straight down.
  - J1 is now SMD lap pads, with snap channels on the S-ledge top for strain relief.
  - J2 takes both LEDs through a Y-splice.
- **TinySLED cradles:**
  - The lattice left nothing under the LEDs, so a pad in each half now runs out to r 71.5 and ties into the R8 skin.
  - Stack, top: pocket floor 26.5 | 0.3 foam | LED | plate.
  - Stack, bottom: plate | LED | 0.3 foam | ceiling 2.5.
- **Receiver** (ELRS Lite flat; the chip antenna is on the board): sits on a tray in the S pocket, 0.4 VHB under it, with a 1 mm fence on W/E/S. The top plate is 0.4 above it. Mount it with the chip end facing S.
- **ESC:**
  - Off the wall on 4 corner posts, no foam on the FETs.
  - Corner shoes (z ≤ 9.6) and keepers (z ≥ 24.8) cup its ends and lip over the N face; 1.1 foam on the top edge.
  - It slides in from the top with the plate off.
- **ESC cooling:** spin pumps air through the bot, roughly 200 Pa at 4000 rpm.
  - In through top-plate slots over the ESC N gap (r ~35).
  - Through S-wall vents into the receiver pocket and past the tray vent.
  - Out through top-plate slots at r ~57.
- **Ring bolts:** Ti M3×20 button heads seated on Ø7 spot faces at z 3.3. Inserts at z 19.3…25.0, flush with the top spot faces.

## Harness (see `harness/harness.js`)
- **Battery → J6:** XT30, 20 AWG, into the solder cups from above.
- **J7 ↔ switch:** through the N-stop notch to the switch tabs.
- **J1 → ESC power:** 20 AWG through the ledge snap channels.
- **Motors → ESC:** the motor's own ~70 mm silicone leads, twisted, fold in the side corridors and go into 2 mm bullets. The bullets lie between the ESC and the S-ledge face (y −32.1), then short ESC pigtails take over.
- **J4 → ESC signal and J5 → receiver:** GH-4 cables, both in the S groove.
- **LEDs → J2:** both TinySLEDs through a Y-splice. The bottom lead runs under the S beam in the 1.5 mm gap.
- **XIAO USB-C → port:** FPC under the N ledge.
- **Balance lead:** the XH-4P plug sits high in the S gap.

## Open
- **Bring-up:** AM32 current limit 4–5 A/ch to start. Spin-test 3 min with a thermocouple on the FETs.
- **J4 pin mapping:** which pins carry DShot, telemetry and GND.
- **PCB:** layout and routing in KiCad (rev 2 is placement + keepouts only).
- **Your call:** plate material and tooth choice.
- **Not yet checked:** the W rib span over J7 (the FEA only loads the E rib).
- **Before the full MJF order:** fit coupons for the ESC slot and shoes, LED pockets, XT30 windows, J1 snap channels and insert bores.
