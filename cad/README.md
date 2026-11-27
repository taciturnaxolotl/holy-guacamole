# CAD

| Folder | What |
|---|---|
| [`chassis/`](chassis) | Chassis v3.4h (12 mm wheels), as delivered: every part as STEP (`step/`), the TPU ear liners, the wiring harness model and its checker, the offline 3D viewer (`viewer/holy-guacamole.html`) and renders, the generator and FEA scripts, and the vendor motor/switch models they import. The check results (mass, fit, print, FEA, harness) are summed up at the top of its README; the raw logs are not kept. Its README has the Z table and the change history |
| [`fab/`](fab) | What to order and where: the cut DXFs for the weapon ring and the plates, and the list of MJF and printed parts |
| [`rev2/`](rev2) | The carrier board's outline and keepouts (`board_outline.dxf`, `keepout.dxf`) and the placement notes the board scripts follow |

The full-assembly STEP and the viewer-only STLs (fasteners, harness, detailed ESC) from the delivered package are not kept here: the assembly is the `chassis/step` parts in one file, and the viewer already has the rest built in.
