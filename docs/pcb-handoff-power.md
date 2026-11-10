# Handoff: rev-2 carrier power layout (from the chassis/review session, 2026-11-10)

Board checked: `guac.kicad_pcb` at `c8054af` (copper unchanged since `96137c3`, the PCBWay reroute).
Coordinates are chassis/board mm: origin on the spin axis, +x E, +y N (KiCad x = 80 + x, KiCad y = 65.5 − y).
Prompted by Discord review (IrregularJoe, Camden Wallraff, Robert K). All numbers below are measured from the board file, not estimated.

## What the review found, with numbers

DC solve of the board copper (2 oz outer, 1 oz inner, vias and PTH barrels included, room temperature; add ~20 % hot):

| Path | R | 10 A | 16 A |
|---|---|---|---|
| VBAT_RAW, J6.2 → J7.2 | 5.5 mΩ | 55 mV, 0.55 W | 1.4 W |
| VBUS, J7.1 → J1.1 | 4.9 mΩ | 49 mV, 0.49 W | 1.25 W |
| GND, J1.2 → J6.1 | 0.19 mΩ | 2 mV | ~0 |
| **Total** | **10.6 mΩ** | **0.11 V, 1.1 W** | **0.17 V, 2.7 W** |

1. **The switch detour carries the full ESC current ~90 mm up the E edge and across the N end, twice.** It passes **0.6 mm from U6** (H3LIS, (17.3, 5.0)) on B.Cu and In2, and runs under the XIAO. About 80 % of the 10.6 mΩ is this detour.
2. **Narrow stretches** (2-oz-equivalent width; In2 counts half):
   - VBUS beside J6, y −12…−4: **2.55 mm, F.Cu only** (~10 mm long).
   - VBUS at y ≈ 9, under the XIAO: **2.04 mm, B.Cu only**.
   - VBAT_RAW on the E edge: 3.0–3.1 mm (B.Cu + In2).
   - IPC-2221 (outer, 2 oz), open air: at 10 A these rise ~10–16 °C; at 16 A the B.Cu neck rises ~45 °C. Inside the closed bot it will be worse.
3. **3V3 is the reference plane for the power strips.** About **300 mm² of B.Cu VBUS/VBAT_RAW sits directly under the In2 3V3 pour** (stackup: B.Cu–In2 is the thin prepreg). The HF part of the ESC current returns through the nearest plane, which is 3V3, not GND. This is how "motor spikes hit your 3V3 line" (Robert). Also:
   - In2 3V3 pour runs alongside the In2 power strips for ~47 mm at **0.21 mm**.
   - F.Cu 3V3 trace (16.8, 7.3) → (16.8, 24.2), 0.3 mm wide, **0.55 mm** from the F.Cu power copper for 17 mm (feeds U6).
   - B.Cu `CS_C` passes 0.44 mm from the power copper at (14.0, 3…5); `HEAD_LED` and `SEL_LAT` 0.39 mm at (0.6, 16.5…20.6) and (−5…−9, 15…19).
4. **Not a problem:** the GND return J1 → J6 is 0.19 mΩ and stays in the S end. The VBAT_RAW-out / VBUS-back pair runs side by side (~1 mm), so its fields mostly cancel; the radiating battery → ESC → GND loop is already all in the S end. Only *changing* current induces anything (ESC PWM ripple, mostly supplied by the ESC's own caps and C21).
5. **Stitching:** 71 GND vias. Three B.Cu GND pieces hang on a single via: 43.9 mm² at (16.5, 33.2), 7.4 mm² at (3.3, 25.1), 6.2 mm² at (−2.1, 12.8). Zones already remove true islands (`island_removal_mode 0`).
6. **Stackup mismatch:** Board Setup says 1.0 mm, 1 oz everywhere, 0.1 mm prepreg. The order is 1.6 mm, 2 oz outer. Set the stackup to match (outer 0.07 mm) so fills, DRC and fab notes agree.

## Option B (chosen 2026-11-10): J7 to the SW corner, J2 to the old J7 spot

Kieran OK'd the chassis change. The chassis side (v3.4g) and the board constraints (`cad/rev2/scripts/build_rev2.py` → `keepout.dxf`, branch `chassis-v34g-j7-sw`) are done by the chassis session; this section is the board session's work list. Re-import `keepout.dxf` from that branch before placing.

**Placement (courtyards are the `PLACEMENT_*` layers in the new `keepout.dxf`):**

| Part | Now | v3.4g | Notes |
|---|---|---|---|
| J7 XT30UPB-F | pins (−13.8, 21.8) VBUS / (−13.8, 26.8) VBAT_RAW | **pin 1 VBUS (−13.8, −15.8), pin 2 VBAT_RAW (−13.8, −10.8)**; courtyard x −16.6…−11.0, y −18.6…−8.0 | mirror of J6 (J6.1 GND (13.8, −15.8), J6.2 VBAT_RAW (13.8, −10.8)), so both VBAT_RAW pins sit on y −10.8. SW shelf window opens over it in v3.4g; bottom-plate Ø4 reliefs move with the pins (`BOTTOM_PLATE_THT_RELIEF`) |
| J2 GH-2 (LEDs) | (−14.0, −16.3), opens N | **courtyard x −17.48…−10.52, y 23.0…29.4, opens S**; plug zone x −17.0…−11.0, y 18.5…23.0 | the old J7 spot. Rear pads at y 29.4 stay S of the ledge clamp (29.6). Keep the plug zone and the Y-splice zone (`LED_SPLICE_1P0`, x −17…−11, y 15.4…18.5, ≤ 1.0) free of top-side parts |
| L1 SRP6060FA | centre (−16.3, 14.55) | **centre (−16.3, 11.55)**, courtyard y 8.0…15.1 | 3 mm S so the LED cable has a lead-in to the plug; stays N of the key band (y > 8). Pad 1 (SW node) still faces U2 |
| Q1, R16, R17 | (−8.2, −12.3), (−7.6, −8.5 / −9.6) | **move near the new J2** (e.g. E of the plug zone, x −10…−6, y 18…23, ≤ 1.2 is fine there) | they sit in the new power band, and HEAD_SW is now a short run to J2 |
| LED lead keepout | `LED_BOT_LEAD_0P3`, `LED_TOP_LEAD_1P2`, old `LED_SPLICE_1P0` | **`LED_LEADS_0P3`**: 0.8 mm buffer on (−20.0, −26.95) → (−19.7, −24.0) → (−19.6, −12.0) → (−19.6, 7.0) | both LED leads now run N along the W board edge at z 3.4–4.1, jog E at y 6.5–8 (N of U4, S of L1) and run N in the slot between L1 (x ≤ −12.45) and the buck parts (≤ 1.2 tall) at x ≈ −11.6, z 4.2–5.4. Keep that slot (x −12.4…−10.8, y 8…15.5) to ≤ 1.2 mm parts |

The IMU rotation scan with these placements: feasible window **151…168°, 166° kept** (min clearance 0.90 mm). No IMU moves.

**Copper:**

| Net | Route | Width target |
|---|---|---|
| VBAT_RAW | J6.2 (13.8, −10.8) → J7.2 (−13.8, −10.8) straight across along y ≈ −10.8, on B.Cu + In2 (+ F.Cu where free) | ≥ 6 mm 2-oz-equivalent |
| VBUS (power) | J7.1 (−13.8, −15.8) N to the same band, E along it **stacked over VBAT_RAW** on the other layers, then down the E edge from x ≈ 17…19 to J1.1 (18.2, −27.3) as the S part of today's E-edge strip | ≥ 6 mm 2-oz-equivalent; ≥ 6 vias per layer change |
| VBUS (logic) | thin feed (≈ 0.6–1 mm) from the S power area to U2 VIN (−9.3, 15.45), J2 pin 1, R9 (VBAT_SNS) | < 1 A; route it away from U4/U5/U6 and keep the buck input caps at U2 |
| GND | unchanged (J1.2 → J6.1, 0.19 mΩ) | |

Then **delete** the E-edge-north, N-end and NW power strips. The E edge, the area under the XIAO and U6's surroundings go back to 3V3/GND and signals.

Keep the outer-layer 1 mm VBUS ↔ VBAT_RAW rule (`guac.kicad_dru`): in the stacked band that means VBUS and VBAT_RAW are on **different layers**, never side by side on the same outer layer.

Band contents to clear (y −9…−13, x −12…12): Q1, R16, R17 (moving). U5 (−4.35, −17.47) is ~2.5 mm S of the band edge at y −13; C21 (x 0.3…9.2, y −19.3…−14.4) is just S of it and taps VBUS there.

Expected: power copper ~70 mm instead of ~190 mm, **~1.5–2 mΩ instead of 10.6 mΩ** (~0.15–0.2 W at 10 A), nothing carrying ESC current N of y −8.

**After moving:**
- Re-run DRC against `guac.kicad_dru`, the connectivity check, and the resistance solve (`hardware/scripts/review/rsolve.py`: `python3 hardware/scripts/review/rsolve.py "/Power Subsystem/VBAT_RAW" J6.2 J7.2 10`, `... VBUS J7.1 J1.1 10`).
- In2: with the power gone from the E edge, the 3V3 pour no longer sits over power strips. Check nothing on In2 3V3 overlaps the new band (make In2 under the band GND or power).

## Option A (not taken): keep J7 where it is and harden the board

Do these in this order:

1. **Give the power strips a GND reference.** Rule area on In2 over every B.Cu and F.Cu VBUS/VBAT_RAW strip: no 3V3/5V pour there. Fill In2 under the strips with GND (or with the same power net to double it), stitched to In1/F/B GND.
2. **Pull the In2 3V3 pour ≥ 1 mm back** from the In2 power strips (zone-to-zone clearance rule for `3V3` vs `VBUS`/`VBAT_RAW` on In2).
3. **Re-feed U6's 3V3 from inside the board**: drop the F.Cu trace at x 16.8 (y 7.3…24.2) and take 3V3 from the In2 3V3 plane by a via next to C10/U6.
4. **Move signals off the power strips** to ≥ 1 mm: `CS_C` at (14.0, 3…5), `HEAD_LED` at (0.6, 16.5…20.6), `SEL_LAT` at (−5…−9, 15…19).
5. **Widen the two necks**: VBUS beside J6 (y −12…−4, F.Cu only) gets B.Cu or In2 copper with ≥ 6 vias per transition; VBUS at y ≈ 9 (B.Cu only) gets In2 or F.Cu doubling.
6. Re-run the resistance solve; target ≤ 7 mΩ end to end.

U6 still sits 0.6 mm from the strips in Option A, and the 166° rotation leaves no room to move it. Option A reduces the coupling; it does not remove it.

## Both options

- **Stitching vias**: grid of GND vias (~3–4 mm pitch) wherever F.Cu, In1 and B.Cu GND all exist; a row ~1.5 mm in from the board edge; a fence along both sides of any power strip; ≥ 3 vias per B.Cu GND piece (fix the three above first).
  - Quickest: one via → right-click → Create Array, then DRC and delete the flagged ones.
  - Better: add a stitching stage to the scripted pipeline (after `bridge_rev2.py`): grid candidates, keep those inside all three GND fills with ≥ 0.215 mm to other copper and ≥ 0.41 mm hole-to-hole to component holes; 0.62/0.25 vias (PCBWay normal process, as in `guac.kicad_dru`).
- **Stackup** to 1.6 mm, outer 0.07 mm (finding 6).
- **Keep**: J1/J6 GND return as is; C21 at the S edge; the 1 mm outer VBUS ↔ VBAT_RAW rule.

## Decisions

1. Option B, chassis v3.4g (Kieran, 2026-11-10).
2. The switch stays in the N lobe; the pigtail runs ~85 mm down the W corridor (z ≈ 24, under the shelves, above the motor-screw key path) to J7.
