# Ideas

## Traction Control via eRPM Slip Detection

If we get bidirectional DShot eRPM working, we can implement traction control:

1. Calculate expected wheel RPM from bot angular velocity (omega) and known geometry (wheel radius, track width).
2. Compare expected wheel RPM to actual eRPM from each motor.
3. If a motor's eRPM exceeds expected (wheel spinning faster than the surface speed implies), it's slipping. Reduce that motor's throttle until eRPM converges with expected.

This would improve drift consistency on low-grip surfaces and prevent spin-out during aggressive drift corrections. Requires reliable bidirectional DShot telemetry at control loop rate.

Related: RSSI-as-rotation-sensor research (see chat history 2026-07-13). eRPM gives per-motor ground truth; RSSI gives whole-body rotation without IMUs. Both could complement the existing accelerometer+gyro EKF.

## ESP-NOW as Secondary Sensor + Telemetry Link

Based on Trevor Gower's rotation_sensing project (https://github.com/TGower/rotation_sensing).

Add an ESP32-C3 (bodged via UART to RP2350, or on next PCB rev) running ESP-NOW RX alongside the primary ELRS RC link. Provides:

- Full-rate RSSI for autocorrelation-based rotation estimation and PLL absolute heading (solves theta observability gap).
- Independent omega measurement for IMU cross-validation and redundancy.
- High-bandwidth telemetry backlink for live tuning without consuming CRSF bandwidth.

**Critical:** Use ESP-NOW broadcast mode (no ACK) for high packet rates. Unicast waits for ACK on every frame, killing throughput at 6kHz+ target rates. Broadcast is fire-and-forget but sufficient for sensor data where occasional loss is acceptable.

### Hardware Integration Notes

-   **ESP32 UART pins:** GPIO23 (SWDIO) and GPIO24 (SWDCK) on the XIAO RP2350. SWD is unused in production; these edge pins are accessible without PCB mods. First-rev carrier does not break out XIAO underside pads (D11-D18), so SWD pins are the bodge-friendly option.
-   **Heading LED (GPIO41):** DNP in first rev. Could serve as alternate UART pin if SWD is ever needed.
-   **ELRS CRSF link:** Insufficient for RSSI heading (~21Hz max RSSI update rate). ESP-NOW provides ~6kHz raw RSSI required for autocorrelation/PLL at combat RPM.
