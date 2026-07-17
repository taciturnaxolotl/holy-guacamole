# ELRS Passthrough (RP2350)

A **temporary tool firmware** that turns the XIAO RP2350 into a Betaflight-style
serial passthrough bridge, so you can flash or configure the ELRS receiver
wired to `uart0` using the **ExpressLRS Configurator** — no USB-to-serial
adapter, no transmitter, no WiFi.

The receiver is the only thing on `uart0` (GPIO0 = TX → RX's RX, GPIO1 = RX ←
RX's TX, from `../include/hw_pins.h`), which is exactly where a flight
controller sits. This firmware makes the RP2350 answer like one.

## How it works

1. Presents a USB CDC serial port (raw, no console).
2. Emulates the minimal Betaflight CLI that `BFinitPassthrough.py` checks:
   `#`, `get serialrx_provider|inverted|halfduplex|rx_spi_protocol`, `serial`,
   and `serialpassthrough`.
3. On `serialpassthrough` it becomes a transparent USB↔`uart0` bridge and
   mirrors the host's baud onto `uart0`.
4. The Configurator then sends the ROM training burst + the CRSF
   reboot-to-bootloader command through the bridge, and esptool flashes the
   receiver over the same wire.

Until passthrough is active it does **not** forward `uart0` → USB, so the
receiver's CRSF chatter can't corrupt the CLI handshake.

## Build

```bash
# from repo root, inside the firmware nix shell
nix develop ./firmware --command bash -c \
  'cmake -B firmware/passthrough/build -S firmware/passthrough \
     -DPICO_PLATFORM=rp2350 -DPICO_BOARD=pico2 && \
   cmake --build firmware/passthrough/build -j'
```

Output: `firmware/passthrough/build/elrs_passthrough.uf2`.

## Use it

1. **Flash the tool** (reboots the running board into BOOTSEL automatically):
   ```bash
   picotool load -x firmware/passthrough/build/elrs_passthrough.uf2
   ```
2. Open the **ExpressLRS Configurator**, pick your receiver target
   (e.g. BetaFPV 2.4GHz RX), Flashing Method = **BetaflightPassthrough**,
   select the RP2350's serial port, and Flash. (Or use it just to open the
   web/settings if you only want to reconfigure.)
3. **Restore the flight firmware** when done:
   ```bash
   picotool load -x firmware/build/holy_guacamole.uf2
   ```

## Notes

- This image is standalone; it never runs the flight-control loop.
- Baud is followed live via `tud_cdc_line_coding_cb`, so esptool baud changes
  are handled.
- Verified to build and enumerate; the esptool handshake is best confirmed by
  an actual flash attempt against the receiver.
