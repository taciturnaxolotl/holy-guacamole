import {Circle, Line, Txt} from '@motion-canvas/2d';
import {createSignal, all, waitFor, linear, easeInOutCubic} from '@motion-canvas/core';
import {Stage} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 3) — the gyro redline.
 * Bot spins on the left; on the right we plot what a gyro *reads* vs the true
 * spin rate. It tracks the ideal line only until its ceiling (~4000 °/s ≈ 660
 * rpm), then flatlines while the true spin races on. Pinned and useless at
 * combat RPM — so we reach for accelerometers instead.
 */
export function* gyroRedline(s: Stage) {
  const {view, robot} = s;

  // plot on the right, matching the other graph beats
  const x0 = -40, x1 = 780, W = x1 - x0, yb = 300, Htop = 560;
  const maxRate = 4500, ceiling = 660; // rpm; 660 rpm ≈ 4000 °/s
  const X = (r: number) => x0 + (r / maxRate) * W;
  const Y = (r: number) => yb - (Math.min(r, maxRate) / maxRate) * Htop;
  const p = createSignal(0);

  const xAxis = (<Line points={[[x0, yb], [x1 + 20, yb]]} stroke={theme.gridLine} lineWidth={3} endArrow arrowSize={12} opacity={0} />) as Line;
  const yAxis = (<Line points={[[x0, yb], [x0, yb - Htop - 40]]} stroke={theme.gridLine} lineWidth={3} endArrow arrowSize={12} opacity={0} />) as Line;
  const xLab = (<Txt text={'true spin rate'} fill={theme.grey} fontFamily={fonts.sans} fontSize={30} position={[x1 - 90, yb + 44]} opacity={0} />) as Txt;
  const yLab = (<Txt text={'gyro reads'} fill={theme.grey} fontFamily={fonts.sans} fontSize={30} position={[x0 + 90, yb - Htop - 50]} opacity={0} />) as Txt;

  // faint ideal line (what a perfect sensor would report)
  const ideal = (<Line points={[[x0, yb], [X(maxRate), Y(maxRate)]]} stroke={theme.gridLine} lineWidth={3} lineDash={[10, 10]} opacity={0} />) as Line;
  const idealTag = (<Txt text={'ideal'} fill={theme.grey} fontFamily={fonts.sans} fontSize={24} position={[X(maxRate) - 70, Y(maxRate) - 26]} opacity={0} />) as Txt;

  // gyro ceiling
  const ceil = (<Line points={[[x0, Y(ceiling)], [x1, Y(ceiling)]]} stroke={theme.red} lineWidth={3} lineDash={[8, 8]} opacity={0} />) as Line;
  const ceilTag = (<Txt text={'gyro ceiling  ~4000 °/s'} fill={theme.red} fontFamily={fonts.sans} fontSize={26} position={[x1 - 200, Y(ceiling) - 26]} opacity={0} />) as Txt;

  // gyro reading curve: tracks the ideal, then clips flat at the ceiling
  const gyroPts = () => {
    const maxR = p() * maxRate;
    const pts: [number, number][] = [];
    for (let r = 0; r <= maxR; r += 40) pts.push([X(r), Y(Math.min(r, ceiling))]);
    pts.push([X(maxR), Y(Math.min(maxR, ceiling))]);
    return pts;
  };
  const gyro = (<Line points={gyroPts} stroke={theme.blue} lineWidth={6} opacity={0} />) as Line;
  const dot = (<Circle size={20} fill={theme.yellow} position={() => [X(p() * maxRate), Y(Math.min(p() * maxRate, ceiling))]} opacity={0} />) as Circle;
  const readout = (
    <Txt text={() => `${Math.round(p() * maxRate)} rpm   ·   gyro ${Math.round(Math.min(p() * maxRate, ceiling) * 6)} °/s`}
      fill={theme.white} fontFamily={fonts.sans} fontSize={34} position={[(x0 + x1) / 2, yb - Htop - 90]} opacity={0} />
  ) as Txt;

  const items = [xAxis, yAxis, xLab, yLab, ideal, idealTag, ceil, ceilTag, gyro, dot, readout];
  items.forEach(n => view.add(n));

  // bot left, axes + reference lines up
  yield* all(
    robot.position([-640, 0], 0.9, easeInOutCubic),
    robot.scale(0.85, 0.9, easeInOutCubic),
    xAxis.opacity(1, 0.5), yAxis.opacity(1, 0.5),
    xLab.opacity(1, 0.5), yLab.opacity(1, 0.5),
  );
  yield* all(
    ideal.opacity(0.9, 0.5), idealTag.opacity(1, 0.5),
    ceil.opacity(1, 0.5), ceilTag.opacity(1, 0.5),
  );

  // sweep the spin up: gyro tracks, then pins at the ceiling as true races on
  yield* all(gyro.opacity(1, 0.4), dot.opacity(1, 0.4), readout.opacity(1, 0.4));
  yield* all(
    p(1, 4.5, linear),
    robot.rotation(robot.rotation() + 360 * 9, 4.5, linear),
  );
  yield* waitFor(1.4);

  // clear the graph and recenter the bot for the accelerometer beat
  yield* all(
    robot.position(0, 0.9, easeInOutCubic),
    robot.scale(1, 0.9, easeInOutCubic),
    ...items.map(n => n.opacity(0, 0.6)),
  );
  items.forEach(n => n.remove());
}
