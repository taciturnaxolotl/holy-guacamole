import {Rect, Txt, Line} from '@motion-canvas/2d';
import {createRef, createSignal, all, waitFor, linear, easeOutCubic} from '@motion-canvas/core';
import {Stage} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 3) — the gyro redline.
 * As the bot spins up, a gyro's reading races up a meter and slams into its
 * ceiling (~4000 °/s ≈ 660 rpm) while the true spin keeps climbing far past.
 * The gyro is pinned and useless at combat RPM — motivation for using
 * accelerometers instead.
 */
export function* gyroRedline(s: Stage) {
  const {view, robot} = s;

  // meter geometry (screen space)
  const W = 940, x0 = -470, y = 300;
  const gyroFrac = 0.166; // gyro ceiling (~660 rpm) as a fraction of the ~4000 rpm range

  const rate = createSignal(0); // 0..1 of the displayed spin range

  const track = (
    <Rect x={x0} y={y} offset={[-1, 0]} width={W} height={40} radius={20}
      fill={theme.gridLine} stroke={theme.gridLine} lineWidth={2} opacity={0} />
  ) as Rect;
  const trueBar = (
    <Rect x={x0} y={y} offset={[-1, 0]} width={() => rate() * W} height={40} radius={20}
      fill={theme.blue} opacity={0} />
  ) as Rect;
  const gyroBar = (
    <Rect x={x0} y={y} offset={[-1, 0]} width={() => Math.min(rate(), gyroFrac) * W} height={40} radius={20}
      fill={theme.red} opacity={0} />
  ) as Rect;
  const redline = (
    <Line points={[[x0 + gyroFrac * W, y - 44], [x0 + gyroFrac * W, y + 44]]}
      stroke={theme.red} lineWidth={4} lineDash={[8, 8]} opacity={0} />
  ) as Line;

  const trueTag = (
    <Txt text={'true spin rate'} fill={theme.blue} fontFamily={fonts.sans} fontSize={30}
      x={x0} y={y + 78} offset={[-1, 0]} opacity={0} />
  ) as Txt;
  const gyroTag = (
    <Txt text={'gyro maxes out'} fill={theme.red} fontFamily={fonts.sans} fontSize={30}
      x={x0 + gyroFrac * W} y={y - 74} opacity={0} />
  ) as Txt;
  const rpm = (
    <Txt text={() => `${Math.round(rate() * 4000)} rpm`} fill={theme.white} fontFamily={fonts.sans}
      fontSize={44} y={y - 150} opacity={0} />
  ) as Txt;

  view.add(track); view.add(trueBar); view.add(gyroBar);
  view.add(redline); view.add(trueTag); view.add(gyroTag); view.add(rpm);

  // bring the meter up
  yield* all(
    robot.position([0, -180], 0.8, easeOutCubic),
    track.opacity(1, 0.5),
    trueBar.opacity(1, 0.5),
    gyroBar.opacity(1, 0.5),
    redline.opacity(1, 0.5),
    rpm.opacity(1, 0.5),
  );

  // spin up: the bar climbs, the gyro pins at the redline while true keeps going
  yield* all(
    rate(gyroFrac, 1, linear),
    robot.rotation(robot.rotation() + 360 * 2, 1, linear),
    gyroTag.opacity(1, 0.5),
  );
  // gyro is now clipped — flash the redline as the true rate races ahead
  yield* all(
    rate(1, 2.5, linear),
    robot.rotation(robot.rotation() + 360 * 10, 2.5, linear),
    trueTag.opacity(1, 0.5),
    redline.lineWidth(7, 0.25).to(4, 0.25).to(7, 0.25).to(4, 0.25),
  );
  yield* waitFor(1.2);

  // clear the meter, settle the bot for the accelerometer explanation
  yield* all(
    robot.position(0, 1, easeOutCubic),
    track.opacity(0, 0.6), trueBar.opacity(0, 0.6), gyroBar.opacity(0, 0.6),
    redline.opacity(0, 0.6), trueTag.opacity(0, 0.6), gyroTag.opacity(0, 0.6),
    rpm.opacity(0, 0.6),
  );
  [track, trueBar, gyroBar, redline, trueTag, gyroTag, rpm].forEach(n => n.remove());
}
