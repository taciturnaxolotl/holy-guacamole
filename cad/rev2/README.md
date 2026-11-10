# Rev-2 carrier: outline, keepouts, placement proposal (holy guacamole v33 rev B)

**Source:** `/tmp/hg33b/holy_guacamole_v33b/` (read-only). It has `README.md` (Z table and plan features), `scripts/concept_v33.py` and `step/*.step`.
I took the constants from the script and README and confirmed them with part bounding boxes and planar sections of the rev B STEPs.
The STEPs were tessellated to `/tmp/hg33b_work/` and sliced with trimesh.

**Frame:** the generator's own. Origin on the spin axis, +Y = N (switch/USB), −Y = S (ESC/rx), +X = E, +Z up, viewed from +Z. **Board coordinates = chassis XY**, in mm.

**Tags:** **[M]** = measured from rev B, **[C]** = concept/README constant, **[D]** = decision from the brief, **[A]** = my assumption or proposal.

**Superseded work:** `stale_bodystep/` (old July chassis) and `stale_v33a/` (v33 rev A). Ignore both.

## v3.4e harness keepouts (current)

From the chassis v3.4e `harness.js` (checker now tests U5 directly: 9.8 mm clearance). In `keepout.dxf`, also hard obstacles in the IMU rotation scan (window still 152…168°, 166° kept):

| Layer | Geometry | Limit |
|---|---|---|
| `LED_BOT_LEAD_0P3` | 0.8 mm buffer on (−20.0, −26.95) → (−19.9, −26.6) → (−19.4, −24.0) → (−19.4, −12.0) → (−19.0, −7.5) → (−16.4, −3.7) → (−13.35, −3.9) → (−13.35, −5.8) | no parts (also a no-footprint rule area in the PCB) |
| `LED_TOP_LEAD_1P2` | 0.8 mm buffer on (−17.9, −10.5) → (−17.8, −9.4) → (−17.2, −6.8) → (−15.6, −5.0) → (−14.65, −5.0) → (−14.65, −5.8) | ≤ 1.2 |
| `LED_SPLICE_1P0` | x −15.0…−13.0, y −8.6…−5.6 | ≤ 1.0 |

Note: the top-lead buffer touches the J2 plug zone at its NW corner (x −17.1…−17.0, y −9.7…−8.6); the lead is at z ≥ 4.65 there and ~0.25 mm W of the plug. The chassis checker passes it; worth a look on the first build.

## v3.4e: J2 opens N (current; on top of the v3.4d harness review)

The v3.4d harness put the Y-splice and the top-LED lead over U5 (0.35 / 0.55 mm above the chip). Moving the splice west was not enough: with J2 opening E its pigtail had to U-turn in a 0.57 mm gap under the battery corner. So J2 now opens **N**:

| Item | x | y | Height | Notes |
|---|---|---|---|---|
| J2 header (GH-2, `JST_GH_SM02B-GHS-TB`, rotated so the opening faces +y) | −17.48…−10.52 | −19.5…−13.1 | 4.25 | centre (−14.0, −16.3); back pads along y −19.5 |
| J2 mating plug + cable exit | −17.0…−11.0 | −13.1…−8.6 | 4.25 | cable leaves the N face |
| Y-splice (chassis harness) | about x −14, y ≈ −9.5 | | top ≈ 5.5 | under the L-key sweep (z 6.53 → 4.0 limit), ≥ 5 mm from U5 |

IMU array: 166° rotation kept (window now 152…168°). U5 (−4.35, −17.47) is 4.2 mm E of the J2 header. From now on every `LED_*` keepout except `LED_CORNER` is a hard obstacle in the rotation scan, so a harness route over an IMU fails the check instead of passing silently.

The v3.4d harness layers (`LED_BOT_LEAD_UNDER_BEAM_NO_PARTS`, `LED_BOT_HOOK_0P3`, `LED_TOP_LEAD_1P2`, `LED_SPLICE_1P0`) are removed; nothing runs under the S beam any more. They come back from the v3.4e `harness.js` once the chassis session re-routes.

## v3.4d harness keepouts (chassis session, on top of 1c456dd)

The chassis viewer now carries a collision-checked wiring harness (every wire, plug, bullet and splice against the frame, the parts and each other). It fits 1c456dd; these layers protect the routes on the board side:

| Layer | Region | Limit | Why |
|---|---|---|---|
| `LED_BOT_LEAD_UNDER_BEAM_NO_PARTS` | 0.8 mm either side of (−20, −26.95) → (−15, −24.4) → (−9.6, −22.4) → (−6.2, −21.1) → (−3.0, −20.6) | no top-side parts (vias OK) | bottom TinySLED 2-core lead lies on the board, z 2.7…3.8, under the S beam |
| `LED_BOT_HOOK_0P3` | x −2.0…−0.7, y −20.2…−17.0 | ≤ 0.3 | same lead climbing z 3.4 → 4.6 beside U5 into the splice |
| `LED_TOP_LEAD_1P2` | 0.8 mm either side of (−12.6, −11.4) → (−5.0, −11.8) → (−2.4, −13.2) → (−2.0, −14.8) → (−4.0, −15.37) | ≤ 1.2 | top TinySLED lead under the battery floor, bottom z 4.05 |
| `LED_SPLICE_1P0` | x −7.6…−1.0, y −18…−14 | ≤ 1.0 | Y-splice sleeve x −6.6…−4.0 at y −16.02, bottom z 3.85 (U5 fits at 1.0) |

Also:
- `J4_ESC_SIG` / `J5_RX` courtyards split: header body y −29.6…−25.55 (4.25 tall) + `J4_REARPADS` / `J5_REARPADS` y −25.55…−23.2 at 0.2, so the S-beam check stops flagging the flat pads.
- `J1` strain relief: the board has no room for tie slots (pad 2 is 0.3 mm from the board edge, beam to the N, ledge to the S). The chassis adds snap channels for both 20 AWG leads on the S-ledge top (y −31.8…−30.2, slots 1.5 wide at x 14.85…16.35 and 17.65…19.15) just before they drop to the pads; finish each joint with an epoxy fillet. Footprint description updated.
- Chassis side of 1c456dd: shelf windows widened so both mated XT30s go straight down (SE shelf now ends at y −19.2; NW gap y 18.6…30.0), and TinySLED cradles added under both LED pockets.
- TinySLED current: unchanged, they were already paralleled on Q1 in Rev A.
- `build_rev2.py` takes `WORK` / `MPFX` env vars, so the checks can slice the chassis v3.4d STLs (`MPFX=v33m_`) instead of rev B.

## v3.4c update (current; supersedes the placement tables further down)

The chassis designer's v3.4c constraints are encoded in `scripts/build_rev2.py` as boxes (no v3.4c STEP yet; the section checks and overview PNGs still slice v33b meshes). New keepout layers: `S_BEAM_1P2`, `S_GAP_XH_PLUG_LOW_PARTS`, `MOTOR_SVC_LOOP_7P5`, `LED_CHANNEL_MOUTH_CLEAR`; `BATTERY_4P7` is now |x| ≤ 9.0, y −19.8…29.9; ribs at |x| 8.75…10.75.

| Constraint (v3.4c) | Value |
|---|---|
| Battery | GNB 3S 380, 55 × 17 × 20, x ±8.5, y −23.2…+31.6, bottom z 7.2; leads + XH-4P out of the S end |
| Upper ribs | \|x\| 8.75…10.75 from z 16.9, y 11…32.7 and −22.5…−11 |
| S cross-beam | full width, y −24.8…−19.8, z 4.0…7.2 → ≤ 1.2 mm parts under it |
| S gap | y −29.9…−24.8: XH plug and motor leads pass above; low parts only |
| Motor-lead service loop | x ±(14…17.5), y −28…−20, z 10…22 |
| Phase bullets | y −34…−30, z 10…22 (under the ledge, no board impact) |
| Shelf windows | J6 under the SE shelf end (y < −15.1); J7 in the NW gap y 21.8…29.0 |

| Part | Courtyard x | Courtyard y | Height above board | Notes |
|---|---|---|---|---|
| J6 battery XT30 (XT30UPB-M) | 11.0…16.6 | −18.6…−8.0 | mated ≈ 21 [A] | rotated 90°, pins (13.8, −15.8) / (13.8, −10.8) |
| J7 switch XT30 (XT30UPB-F) | −16.6…−11.0 | 19.0…29.6 | mated ≈ 21 [A] | rotated 90°, pins (−13.8, 21.8) / (−13.8, 26.8) |
| L1 SRP6060FA | −19.35…−12.45 | 11.0…18.1 | 5.8 | moved S out of J7 |
| U2 buck block | −10.0…−2.7 | 8.3…22.1 | ≤ 1.2 | unchanged |
| C21 100 µF 25 V polymer tantalum, 7343-43 | 0.5…9.0 | −19.3…−14.3 | ≤ 4.3 | was a 6.3 × 5.8 can in the NW; now in the battery strip, ~12 mm from J1 |
| D2 SMAJ15CA | 12.6…19.6 | −7.7…−4.2 | 2.2 | moved into the key band (limit 4.0), clear of J6 |
| J1 ESC power, 2 SMD lap pads 2.6 × 4.0 | 13.7…19.5 | −29.3…−25.3 | ≈ 0.5 (+ wire 0.8) | **routed board (v34e layout): pad 1 VBUS at x 16.9…19.5 (E, on the edge power strip), pad 2 GND at x 13.7…16.3**; south of the beam. No longer through-hole |
| J4 ESC signal GH-4 | 4.27…13.73 | −29.6…−23.2 | 4.25 | centre (9.0, −26.4), opens S into the groove. Body y −29.6…−25.55; only the flat rear pads sit under the beam |
| J5 receiver GH-4 | −5.23…4.23 | −29.6…−23.2 | 4.25 | centre (−0.5, −26.4), same as J4 |
| J2 TinySLEDs GH-2 (both LEDs) | −19.7…−13.3 | −19.5…−12.54 | 4.25 | opens E, plug zone x −13.3…−7.4. J3 deleted; the two LEDs share one plug through a Y-splice in the harness |
| XIAO | −2.17…15.61 | 7.86…28.82 | 3.2 (USB-C 4.3) | unchanged |
| IMUs | | | ≈ 1 | 166° rotation still clear (window 163…168°) |

Through-hole pins left (bottom-plate Ø4 reliefs, layer `BOTTOM_PLATE_THT_RELIEF`): J6 (13.8, −15.8), (13.8, −10.8); J7 (−13.8, 21.8), (−13.8, 26.8). J1's two reliefs can go.

LED lead route: from the SW channel mouth (x −20…−19, y −28.5…−25.5, z < 4) north under the S beam (1.5 mm clear between board top 2.5 and beam bottom 4.0, enough for two 28 AWG) to J2's plug at y ≈ −16. The channel mouth stays clear.


Regenerate:
```
U="uv run --with cadquery --with shapely --with ezdxf --with trimesh --with matplotlib --with networkx --with scipy --with rtree"
$U python scripts/slice_v33b.py      # sections/ (+ tessellates STEPs to /tmp/hg33b_work)
$U python scripts/build_rev2.py      # board_outline.dxf, keepout.dxf, overview PNGs, scripts/build_rev2_checks.txt
```

## Files
- `board_outline.dxf`: R2000, mm. `Edge.Cuts` is a closed loop of 8 LINE + 8 ARC. `Holes` has 4 × Ø2.2 CIRCLE. Both DXFs pass an ezdxf audit with 0 errors.
- `keepout.dxf`: R2000, mm. It holds:
  - one layer per keepout region; height limits are in the layer name, for a 1.6 mm board;
  - `PLACEMENT_*` layers with one courtyard rectangle per proposed part;
  - `REF_*` layers with v33b/v34 features.
- `sections/` (generated, not tracked; run the two commands under "Regenerate"):
  - `v33b_z±NN.NN.{dxf,png}`: lower/upper/plate sections at 19 heights from z 0.1 to 28.8, one DXF layer per part.
  - `solid_*.wkt`: the same sections as shapely WKT.
  - `rev2_overview_{bay_z+01.50,lower_z+04.50,ribs_z+20.00}.png`: board, keepouts and placements over the chassis.
- `scripts/`: `slice_v33b.py`, `build_rev2.py` (all geometry checks and the IMU rotation scan; results in the generated, untracked `build_rev2_checks.txt`), `bboxes.py`, `pcbcomp.py` (Rev A component heights).

## Board outline [D, checked M]
- **40.0 × 76.0**, x ±20, y ±38, corner R1.5, centred on the spin axis.
- **USB notch kept:** x 0.4…13.0 from y 29.2 to the N edge, inner corners R1.0, mouth corners R0.5.
  Rev B still has the plug channel (N-ledge void x 0.7…12.7, y 29.9…39.5 at z 2.2 and 5.0 [M]). Board ∩ channel = 0 [M].
- Clearance to the bay walls (|y| < 29.9): **0.50** [M].
- Lower-half solid over the board footprint exists only inside the end-ledge blocks (z 0.95…7.15) [M]. Nothing from the lower half is above the board at z ≥ 7.25.
- Upper half over the board [M]:
  - ribs |x| 6.5…8.5, y 11…33 and −33.5…−11, from z 16.88;
  - shelves out to the board edge, from z 25.5 (solid at z 26, not at z 25).
- **Ledge recess (chassis change, v34):** each end ledge needs an underside recess x ±20.5, |y| 29.9…38.5, z ≤ board top + 0.1 (`REF_LEDGE_RECESS_NEW`). In the generator:
  - replace `_tp`/`tabpk` with that box;
  - set `PCB_T = 1.6`;
  - drop `PCB_TABHOLES` / `tab_ins`.
  The S-groove floor (`PCB_Z+PCB_T+0.2`) follows `PCB_T` automatically.

## M2 mounting holes [D, checked M]
Ø2.2 drill, Ø4.5 keepout. Heads go into Ø4.0 through-holes in the bottom plate (`BOTTOM_PLATE_M2_HEAD_HOLES`).

| hole | x | y | Ø5.2 boss void in ledge (z 3/4.5/6/7) | Ø3.2 insert bore → v34 groove | → v33b groove | → USB channel | → bay wall | → ledge face |
|---|---|---|---|---|---|---|---|---|
| NW | −16.6 | +34.5 | 0 | — | — | 15.7 | 2.30 | 3.00 |
| NE | +16.6 | +34.5 | 0 | — | — | **2.30** | 2.30 | 3.00 |
| SW | −17.0 | −34.5 | 0 | 10.9 | **1.90** | — | 2.30 | 3.00 |
| SE | +17.0 | −34.5 | 0 | **1.90** | 10.9 | — | 2.30 | 3.00 |

- All four land on solid ledge and clear the grooves.
- With the v34 mirror, the SE insert bore has a 1.5 mm wall to the groove edge (x 13.5). That passes the MJF 1.0 minimum, but a Ø5.2 boss would break into the groove by 0.5.
  **Done (v34):** the S holes are at x ±17.0, giving 1.9 mm to both the groove and the bay wall.
- **Insert length:** the ledge above the recess is 7.2 − (board top + 0.1), i.e. 4.6 for a 1.6 board. Keeping 1 mm of cap means **a 3 mm M2 heat-set** (≤ 3.6).
- **M2 head height:** must be ≤ 1.23 to stay flush with the plate underside (0.32 gap + 0.91 plate). Use a wafer/ultra-low head (k ≈ 0.8–1.0) [A]. A standard M2 pan head (k 1.3–1.6) protrudes by up to 0.4.

## Z budget (board bottom z 0.9 [D]) [C/M]
| item | z | 0.91 board | **1.2 board** | **1.6 board** |
|---|---|---|---|---|
| bottom plate | −0.33…0.58 | | | |
| gap under board | 0.58→0.90 | 0.32 | 0.32 | 0.32 |
| board top | | 1.81 | 2.10 | 2.50 |
| ledge recess ceiling (top + 0.1) | | 1.91 | 2.20 | 2.60 |
| v34 S-groove floor / top | PCB_Z+T+0.2 / 7.3 | 2.01 / 7.3 | 2.30 / 7.3 | 2.70 / 7.3 |
| motor-screw L-key band (\|y\| ≤ 8) | 6.53 | 4.72 | 4.43 | **4.03** |
| battery floor = ledge top = USB channel ceiling | 7.2 | 5.39 | 5.10 | **4.70** |
| groove wires (top 7.3) | 7.3 | 5.49 | 5.20 | **4.80** |
| motor-lead entries (y −25…−15) | 9.8 | 7.99 | 7.70 | **7.30** |
| ribs | 16.88 | 15.07 | 14.78 | **14.38** |
| shelves (corridors) | 25.5 | 23.69 | 23.40 | **23.00** |
| top-plate underside | 28.42 | 26.61 | 26.32 | 25.92 |
| XIAO shield top (+3.19) / USB-C top (+4.30) [M, Rev A model] | | 5.00 / 6.11 | 5.29 / 6.40 | 5.69 / **6.80** |
| USB-C margin to battery / channel ceiling 7.2 | | 1.09 | 0.80 | **0.40** |

- **Foam:** none fits in the 0.32 gap. The underside carries only flush B.Cu test pads and the M2 heads (in plate holes).
- **Through-hole parts are a problem:** J6/J7 (XT30UPB, Ø1.8 drill) and J1 (Ø1.15). Their pin tails and solder fillets do not fit in 0.32.
  Either trim flush and add bottom-plate relief windows (`BOTTOM_PLATE_THT_RELIEF`: Ø4.0 at the 6 pins, through the 0.91 plate), or use SMD-tab variants [A].
- **Bottom plate re-cut:** remove the two v33b Ø6.5 tab-head holes at (−24.75, 24) and (24.5, −24) (open 28.2 mm² each [M]). Add the 4 M2 head holes and the THT reliefs.

## Keepout layers (`keepout.dxf`, limits for a 1.6 board; add 0.4 for 1.2)
| layer | region (x; y) | meaning |
|---|---|---|
| BATTERY_4P7 | −6.5…6.5; −29.9…29.9 | battery footprint (x ±6) + 0.5, between the ledges; parts ≤ 4.7 |
| KEYBAND_4P0 | 3.75 ≤ \|x\| ≤ 20; \|y\| ≤ 8 | 2.5 mm L-key sweep to the motor screws (lowest z 6.53); parts ≤ 4.0 |
| MOTOR_LEADS_7P3 | 8.5 ≤ \|x\| ≤ 20; −29.6…−15 | lead-channel entries (y −25…−15, z 9.8…19.2) and the run S to the ESC; parts ≤ 7.3 |
| RIB_14P4 | 6.5 ≤ \|x\| ≤ 8.5; y 11…33 / −33.5…−11 | rib bottoms at z 16.88 |
| CORRIDOR_23P0 | 8.5 ≤ \|x\| ≤ 20; \|y\| ≤ 29.9 | shelf bottoms at z 25.5 (\|y\| 8…11 is actually open to the top plate, 25.9) |
| LEDGE_CLAMP_NO_PARTS | \|y\| ≥ 29.6, except the v34 groove | under the ledge recess: no top-side parts |
| S_GROOVE_WIRES_4P8 | −4.5…13.5; −38…−29.9 | v34 groove over the board: J4/J5 plugs and wires only |
| BOTTOM_FLUSH_PADS_ONLY | whole board | 0.32 gap to the plate |
| XT30_BAT | 8.5…19.7; −14.6…−8.4 | J6 courtyard |
| XT30_SW | −19.7…−8.5; 22.3…28.5 | J7 courtyard |
| ESC_EDGE | 4.77…19.75; −29.9…−23.2, plus 12.6…19.75; −23.2…−16.9 | J4, J1, D2 (ESC signal and power landing) |
| USB_CHIMNEY | 0.7…12.7; 28.82…38, plus notch 0.4…13.0; 29.2…38 | USB-C overhang and plug path; nothing else here |
| LED_CORNER | −20…−7.2; −29.6…−15.44, plus the channel mouth −20…−19; −28.5…−25.5 | J2/J3 and their plugs |
| RX_ENTRY | −3…3; −29.9…−23.2 | rx leads drop from the groove into J5 |
| MOUNT_KEEPOUT | Ø4.5 at the 4 holes | |
| BOTTOM_PLATE_M2_HEAD_HOLES / BOTTOM_PLATE_THT_RELIEF | Ø4.0 circles | for the bottom-plate cut file |
| IMU_CENTRE | (0,0) | |
| REF_* | bay, ledges, new ledge recess, USB channel and chimney, battery, ESC envelope, S groove v33b and v34, rx, rx lead groove, LED lead channel, switch and its slot, motor lead channels, old tab holes, board | |

## Placement proposal (`PLACEMENT_*`, courtyard rectangles, top side) [A unless noted]
| ref | x | y | centre / pins | h above board | zones / notes |
|---|---|---|---|---|---|
| U1 XIAO | −2.17…15.61 | 7.86…28.82 | Rev A position | 3.2 | USB-C receptacle centred on the channel. **8.67 mm of its 17.78 width (49 %, 182 mm²) is in the battery strip; 8.17 mm is directly under the battery.** Touches the key band by 0.14 (module PCB only). |
| U1 USB-C | 2.25…11.19 | 23.6…30.9 | mouth 1.2 into the channel (starts y 29.7) | 4.3 | 0.40 to the battery and channel ceiling. Max E shift keeping the receptacle in the channel is +1.5 (only for a plug ≤ 9.96 wide); not taken. |
| J7 XT30 (sw loop) | −19.7…−8.5 | 22.3…28.5 | pins (−16.6, 25.4), (−11.6, 25.4) | mated ≈ 21 [A] → top 23.5 | NW corridor; v34 opens a shelf gap at y 21.8…29.0 over it, so the plug goes straight down. Keep J7 inside that window. Leads go up to the switch tabs at x −7.2…−2.8, y ≈ 38, z ≥ 17.7. |
| L1 SRP6060FA | −19.35…−12.45 | 15.1…22.2 | (−15.9, 18.65) | 5.8 | NW corridor. |
| C21 100 µF 6.3×5.8 | −19.5…−10.1 | 8.0…15.1 | (−14.8, 11.55) | 5.8 | NW corridor, body 0.25 N of the key band. **See conflict 1.** |
| U2 buck zone | −10.0…−2.7 | 8.3…22.1 | AP63301 + passives | ≤ 1.2 | partly in the battery strip (fine at this height). |
| J6 XT30 (battery) | 8.5…19.7 | −14.6…−8.4 | pins (11.6, −11.5), (16.6, −11.5) | mated ≈ 21 [A] → top 23.5 | SE corridor, 0.4 clear of the key band (y −8) and of the lead entries (y −15). v34: the SE shelf now ends at y −15.1, so the mated plug goes straight down beside the battery. |
| D2 SMAJ15CA | 12.6…19.6 | −20.4…−16.9 | (16.1, −18.65), horizontal | 2.2 | SE, between J1 and J6. |
| J1 ESC power (20 AWG) | 16.45…19.75 | −29.3…−20.7 | pads (18.1, −27.4), (18.1, −22.6) | 2.5 | SE corner, just inside the S ledge face. |
| J4 ESC signal (GH-4) | 4.77…14.23 | −29.6…−23.2 | (9.5, −26.4), **opening S** | 4.25 | Plug (≈ 6.75 wide [A], x 6.1…12.9) lies in the v34 groove (4.8 high). |
| J5 RX (GH-4) | −4.73…4.73 | −29.6…−23.2 | (0.0, −26.4), **opening S** | 4.25 | Plug at x −3.4…3.4, directly under the rx lead drop (x ±3). |
| J3 TinySLED bottom (GH-2) | −19.5…−13.1 | −29.6…−22.64 | (−16.3, −26.12), rotated 90°, **opening E** | 4.25 | At the SW lead-channel mouth (y −28.5…−25.5). |
| J2 TinySLED top (GH-2) | −19.5…−13.1 | −22.4…−15.44 | (−16.3, −18.92), **opening E** | 4.25 | |
| J2/J3 plugs | −13.1…−7.2 | −29.6…−15.44 | | 4.25 | |
| U4 LSM6DSV320X (r 12) | box ±2 | | **(−11.64, 2.90)**, 166° | ≈ 1 | key band W (fine). 3.4 from the buck zone, 3.1 from C21. |
| U5 H3LIS331 (r 18) | box ±2 | | **(−4.35, −17.47)**, 256° | ≈ 1 | battery strip (fine). 0.85 from the J2/J3 plug zone. |
| U6 H3LIS331 (r 18) | box ±2 | | **(17.30, 4.96)**, 16° | ≈ 1 | key band E (fine). |

### IMU array
- The nominal positions (firmware `imu_geom.c`: r 12 @ 0°, r 18 @ 90°, r 18 @ 210°) are U4 (12, 0), U5 (0, 18), U6 (−15.6, −9). **U5 lands under the XIAO** [M]. The other two are clear but sit in the key band, which is fine at 1 mm.
- A rigid-rotation scan in 1° steps against the board edge, ledges, groove, holes and all placements found only **164…168° CCW** feasible. I chose **166°**, which gives 0.85 mm minimum clearance.
- The radii stay the same, so the centroid geometry and r-ratios are unchanged. In firmware, add 166° to every `angle_rad` (0 → 166°, 90 → 256°, 210 → 16°).
- Rotate the IMU footprints by 166° as well, or keep 0/90° footprints and handle the sensor-axis rotation in firmware [A]. 180° is not feasible: U6 would hit the XIAO's SE corner.

### Where the off-board items are relative to the outline [C/M]
- **USB chimney:** the plug channel is x 0.7…12.7 from y 29.7, z < 7.2, under the N ledge, into the chimney at y 48…58. The USB-C female sits on shelves at z 19.4…21.4 (`usbf` z 21.4…28.0). That is 10–20 mm N of the board edge.
- **Switch:** x −8.18…−1.82, y 37.8…56.85, z 15.5…28.2, centred on (−5, 50.5). The tabs come through the N-wall slot (x −7.2…−2.8, z ≥ 17.7) with tips at y 37.8, which is directly above the board's N edge (y 38). J7 is 9–13 mm SW of the tabs.
- **ESC:** 5 mm envelope x ±13, y −39.3…−34.3, z 7.25…27.25 (real board y −39.3…−37.3) on the S ledge. Its pad edge is its bottom edge at z 7.25 over the v34 groove.
  - Power leads (E side): over or through the groove, then down the ledge face (y −29.9) to J1.
  - Signal leads: into the groove to the J4 plug.
- **ELRS rx:** x ±5.5, y −55…−45, z 25…28, 7 mm S of the board. Its leads run along the groove x ±3, y −45.5…−39 at z ≥ 27.35, down the 3 mm gap beside the ESC, then into the ledge groove and J5.
- **TinySLEDs:** radial at 225°, r 38…59.75. ledT is z 26.8…28.4 and ledB z 0.62…2.2 (bbox x/y −44.5…−24.6) [M]. Both leads enter at the SW channel x −28.5…−19, y −28.5…−25.5:
  - bottom leads at z < 4.0, i.e. 1.5 above a 1.6 board top;
  - top leads at z ≥ 25.

## Conflicts / open items
1. **C21: the brief places it twice** (with J1/D2 at SE, and with L1 in a y 10…28 corridor). SE has no room for the 9.4 × 7.1 courtyard once J1, D2, J4, J5 (with plugs), J6 and the key band are placed. So C21 is NW, about 45 mm of trace from J1.
   If it is meant as the ESC-feed bulk cap, add local ceramics at J1 (e.g. 2 × 1210) or re-plan [A].
2. **J4/J5 opening S** needs both plugs inside the v34 groove (x −4.5…13.5, 4.8 high at 1.6). That leaves no groove width for the 20 AWG ESC power leads at the E end. They have to run over the S-ledge top in the SE corridor (z ≥ 7.2, x 8.5…20.5) and drop at the ledge face to J1.
   The alternative is to widen the groove E to about x 16 (chassis ask).
3. **J2/J3 can't open W:** the board edge is 0.5 from the bay wall, and the SW lead channel is only 1.5 high above a 1.6 board. So they open E, and the LED leads U-turn to the plug.
4. **XIAO under the battery:** 49 % of its width, USB-C margin 0.40 (1.6 board). A 1.2 board gives 0.80. That is the tightest item in the Z stack.
5. **IMU nominal U5 collides with the XIAO.** The 166° array rotation fixes it; the feasible window is only ±2°, so later moves of J2/J3 plugs, J6 or C21 can close it.
6. **Through-hole J6/J7/J1 vs the 0.32 gap.** Needs plate relief windows or SMD parts. "Nothing on the underside" is otherwise met.
7. **SE M2 hole:** moved to x ±17.0 in v34; 1.9 mm wall to the mirrored groove.
8. The v33b N-ledge XT30 (x 10…18.2, y 33.8…39.45) goes away in rev 2. Both XT30s are on the board, so the `xt30` box and the top-plate depth note that depended on it are moot.
9. **XT30 mated height** (~21, from the v33 box) and **pin tail length** are assumptions; I could not reach the AMASS datasheet. Verify that the J6/J7 wire exits stay under the 25.5 shelves.
10. **Debug access with the bottom plate off:** the whole underside (flush test pads) and the 4 M2 screws are reachable. The board drops out downward once the plugs and the 20 AWG pads are free; top side and edges are not reachable. USB via the chimney works with the top plate off and the battery in.
