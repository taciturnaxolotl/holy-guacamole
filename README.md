# Holy Guacamole 🥑

<a href="https://certification.oshwa.org/us002836.html"><img height="75" align="right" src="https://cdn.hackclub.com/019f6b55-59f9-70f2-9f91-930d22f245d3/oshwa-badge.svg"/></a>

![the assembled cad](https://cdn.hackclub.com/019f58d4-a10e-7756-9e08-dc0abd3956e4/edited-image.png)

This is a meltybrain style combat robot whose main weapon is simply its own spinning kinetic energy. The BOM is on a google sheet [here](https://docs.google.com/spreadsheets/d/1paAJ0Wakvn5M726pM15FUGLVGKdC47_Wt41PN1yA9PQ/edit?gid=0#gid=0) and the CAD is done in onshape and available [here](https://cad.onshape.com/documents/a046eeb92ff2319e557090a2/w/6774deed54414bae93c63cc1/e/4d0675cbf797ff5c6c8f60bb?renderMode=0&uiState=6a4b13893c4a31ee1cf2e4f3)

The canonical repo for this is hosted on tangled over at [`dunkirk.sh/holy-guacamole`](https://tangled.org/dunkirk.sh/holy-guacamole)

## Repo map

- [`docs/spec.md`](docs/spec.md): the robot and the rev 2 carrier board (4 layers, 2 oz outer copper, 3S only, made by PCBWay)
- [`docs/firmware.md`](docs/firmware.md): what the firmware and the simulator do today
- [`hardware/procurement/bom_rev2.csv`](hardware/procurement/bom_rev2.csv): the rev 2 parts list
- [`cad/rev2/README.md`](cad/rev2/README.md): what the board takes from the chassis (outline, keepouts, placement)
- [`hardware/`](hardware): the KiCad project. Scripts place and route the board, so it can be rebuilt from the schematic:

```sh
cd hardware && kicad-cli sch export netlist -o /tmp/rev2.net guac.kicad_sch
# the next two need KiCad's own python (it ships pcbnew); this is the macOS path
KIPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KIPY scripts/layout_rev2.py && $KIPY scripts/power_rev2.py
sh scripts/route_best_rev2.sh guac.kicad_pcb   # autoroute (Freerouting 2.5, JDK 25+), then stitching and silk
sh scripts/export_pcbway.sh                    # order files into production/pcbway/
```

| | | | |
|---|---|---|---|
| ![front copper](https://l4.dunkirk.sh/i/B3zZRVosO1XD.webp) | ![back copper](https://l4.dunkirk.sh/i/vYjFfVZuXrg_.webp) | ![inner 1 copper](https://l4.dunkirk.sh/i/HOcu8oD0EThD.webp) | ![inner 2 copper](https://l4.dunkirk.sh/i/nMP7O4GS9EUh.webp) |

| | |
|---|---|
| ![top level schematic](https://l4.dunkirk.sh/i/9V5wneoi2zWS.svg) | ![power subsystem schematic](https://l4.dunkirk.sh/i/2hsbjTacNNWh.svg) |
| ![imu array schematic](https://l4.dunkirk.sh/i/YgQP8xBYWs_f.svg) | ![heading led schematic](https://l4.dunkirk.sh/i/xx49w-yISmpK.svg) |

<p align="center">
    <img src="https://raw.githubusercontent.com/taciturnaxolotl/carriage/main/.github/images/line-break.svg" />
</p>

<p align="center">
    <i><code>&copy; 2026-present <a href="https://dunkirk.sh">Kieran Klukas</a></code></i>
</p>

<p align="center">
  <a href="https://tangled.org/dunkirk.sh/holy-guacamole/blob/main/LICENSE.md"><img src="https://img.shields.io/static/v1.svg?style=for-the-badge&label=Hardware&message=CERN-OHL-S+v2&logoColor=d9e0ee&colorA=363a4f&colorB=b7bdf8"/></a>
  <a href="https://tangled.org/dunkirk.sh/holy-guacamole/blob/main/LICENSE.md"><img src="https://img.shields.io/static/v1.svg?style=for-the-badge&label=Firmware%20%26%20Docs&message=MIT&logoColor=d9e0ee&colorA=363a4f&colorB=b7bdf8"/></a>
</p>
