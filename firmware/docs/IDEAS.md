# Ideas

## Traction Control via eRPM Slip Detection

If we get bidirectional DShot eRPM working, we can implement traction control:

1. Calculate expected wheel RPM from bot angular velocity (omega) and known geometry (wheel radius, track width).
2. Compare expected wheel RPM to actual eRPM from each motor.
3. If a motor's eRPM exceeds expected (wheel spinning faster than the surface speed implies), it's slipping. Reduce that motor's throttle until eRPM converges with expected.

This would improve drift consistency on low-grip surfaces and prevent spin-out during aggressive drift corrections. Requires reliable bidirectional DShot telemetry at control loop rate.

eRPM also gives per-motor ground truth that could complement the existing accelerometer+gyro EKF.
