# Ordering the chassis parts

Everything here is chassis v3.4h (12 mm wheels), in mm, in the chassis frame (origin on the spin axis, +Y = N, the switch and USB end). The source of truth is the STEP set in [`../chassis/step`](../chassis/step); the DXFs are cut from it with `export_dxf.py` and checked with `check_dxf.py`.

## What to order

| Part | Qty | Process | Material | File |
|---|---|---|---|---|
| Lower half | 1 | MJF | PA11 | `../chassis/step/v33m_lower.step` |
| Upper half | 1 | MJF | PA11 | `../chassis/step/v33m_upper.step` |
| Top plate | 1 | MJF with the halves (default), or laser-cut sheet | PA11 0.8 mm | `../chassis/step/v33m_top.step` or `dxf/plate_top_0.8mm.dxf` |
| Bottom plate | 1 | MJF with the halves (default), or laser-cut sheet | PA11 0.8 mm | `../chassis/step/v33m_bot.step` or `dxf/plate_bottom_0.8mm.dxf` |
| Weapon ring | 1 | laser or waterjet (SendCutSend, OSH Cut and the like) | AR550, 3/16" (4.76 mm) | `dxf/ring_AR550_4.76mm.dxf` |
| Ear liners | one set of the fit you keep | FDM, at home | TPU | `../chassis/liners/*.stl` (three fits; see the chassis README) |
| Wheel hubs | 2 (+ spares) | MJF with the halves | PA11 | `../chassis/scripts/wheel_hub.step` (or `wheel_mould/wheel_hub.stl`) |
| Wheel treads | 2 (+ spares) | cast at home in the printed mould | VytaFlex 40, 5.0 cc each | `wheel_mould/` (mould STLs + casting steps) |

The carrier board is ordered separately, from `hardware/` (see `hardware/scripts/export_pcbway.sh`).

## The cut files

| File | Size | Contours | Smallest cutout | Thinnest web |
|---|---|---|---|---|
| `ring_AR550_4.76mm.dxf` | 156.0 × 180.0 | 8 (outline, bore, 6 bolt holes Ø3.40) | 3.40 mm | 3.3 mm |
| `plate_top_0.8mm.dxf` | 115.9 × 126.6 | 12 (outline, 4 screw holes Ø2.8, vents 1.2 mm wide, USB slot) | 1.2 mm slot | 2.85 mm |
| `plate_bottom_0.8mm.dxf` | 115.9 × 126.6 | 14 (outline, 4 screw holes Ø2.8, PCB screw clearances, XT30 tail reliefs Ø4) | 2.8 mm | 20 mm |

Every contour is closed, units are millimetres, and there is no text or construction geometry in the files. The ring's round edges and bolt holes are true arcs and circles (the generator builds the ring as a polygon; `export_dxf.py` fits the arcs back), so they cut round instead of as ~10 mm flats. A `.png` preview sits next to each DXF.

Before ordering:

- **Ring material.** Many services stock AR500 rather than AR550 at 3/16". AR500 is the usual substitute for combat robots, a little softer and tougher; the spec and the FEA assume AR550.
- **Ring bolt holes.** They are Ø3.40 in 4.76 mm plate, about 0.7 times the thickness. Hardened plate often has a minimum hole size near the material thickness. If the service will not cut them, have them cut undersize (or marked) and drill them out to Ø3.4.
- **Ring thickness.** 3/16" AR plate often runs over nominal. Measure the ring when it arrives and regenerate the halves with the measured value before the MJF order (`RING_T_MEAS=<mm>` for `concept_v33.py`, see the chassis README), or order the halves after the ring.
- **Plates in sheet.** The pockets and screws assume 0.8 mm. A 0.031" (0.79 mm) sheet of G10, polycarbonate or aluminium cut from the DXF drops straight in; thicker sheet sits proud of the 0.6 mm pocket.
- **Fit coupons.** The chassis README lists the features worth printing as coupons first (ESC slot and shoes, LED pockets, XT30 windows, J1 snap channels, insert bores).

## Not in this package

Fasteners, inserts, bearings, motors, the battery, the ESC, the receiver and the switch are bought parts; their bodies in `../chassis/step` are for fit checks only.

## Regenerating

```sh
cd cad/fab
uv run --with cadquery-ocp --with ezdxf python export_dxf.py
uv run --with ezdxf --with shapely --with matplotlib python check_dxf.py dxf/*.dxf
```
