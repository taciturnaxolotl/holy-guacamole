import {Circle, Line, Rect, Txt} from '@motion-canvas/2d';
import {createSignal, all, waitFor, linear, easeInOutCubic} from '@motion-canvas/core';
import {Stage} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 4b) — g-force grows with the square of RPM.
 * Because a = ω²r, the felt acceleration rises quadratically with spin rate.
 * The bot sits on the left; on the right we plot g-at-20mm vs RPM. The curve
 * starts buried in the noise floor (low RPM = no signal) and rockets out of it
 * (high RPM = huge clean signal). The pen dot rides the curve as it draws.
 */
export function* gForce(s: Stage) {
  const {view, robot} = s;

  // plot lives on the right, next to the bot
  const x0 = -40, x1 = 780, W = x1 - x0, yb = 300;
  const RPM = 4500, GMAX = 480, gScale = 580 / GMAX;
  const cxp = (x0 + x1) / 2;
  const gAt = (rpm: number) => {
    const w = (rpm * Math.PI) / 30; // rpm -> rad/s
    return (w * w * 0.02) / 9.81;   // a = ω²r at r=20mm, in g
  };
  const X = (rpm: number) => x0 + (rpm / RPM) * W;
  const Y = (g: number) => yb - Math.min(g, GMAX) * gScale;

  const p = createSignal(0); // sweep fraction over the RPM range

  const xAxis = (<Line points={[[x0, yb], [x1 + 20, yb]]} stroke={theme.gridLine} lineWidth={3} endArrow arrowSize={12} opacity={0} />) as Line;
  const yAxis = (<Line points={[[x0, yb], [x0, yb - 600]]} stroke={theme.gridLine} lineWidth={3} endArrow arrowSize={12} opacity={0} />) as Line;
  const xLab = (<Txt text={'RPM'} fill={theme.grey} fontFamily={fonts.sans} fontSize={30} position={[x1 - 20, yb + 44]} opacity={0} />) as Txt;
  const yLab = (<Txt text={'g-force'} fill={theme.grey} fontFamily={fonts.sans} fontSize={30} position={[x0 + 70, yb - 610]} opacity={0} />) as Txt;

  // noise floor near the bottom
  const noiseG = 34, noiseH = noiseG * gScale;
  const noise = (<Rect x={cxp} y={yb - noiseH / 2} width={W} height={noiseH} fill={theme.red} opacity={0} />) as Rect;
  const noiseLab = (<Txt text={'noise floor'} fill={theme.red} fontFamily={fonts.sans} fontSize={24} position={[x0 + 100, yb - noiseH - 22]} opacity={0} />) as Txt;

  // curve grows point-by-point up to the current RPM, so the pen dot always
  // sits exactly on the drawn line (no spline overshoot, no arclength drift)
  const curvePts = () => {
    const maxRpm = p() * RPM;
    const pts: [number, number][] = [];
    for (let rpm = 0; rpm <= maxRpm; rpm += 45) pts.push([X(rpm), Y(gAt(rpm))]);
    pts.push([X(maxRpm), Y(gAt(maxRpm))]);
    return pts;
  };
  const curve = (<Line points={curvePts} stroke={theme.blue} lineWidth={6} opacity={0} />) as Line;
  const dot = (<Circle size={20} fill={theme.yellow} position={() => [X(p() * RPM), Y(gAt(p() * RPM))]} opacity={0} />) as Circle;
  const readout = (
    <Txt text={() => `${Math.round(p() * RPM)} rpm   ·   ${Math.round(gAt(p() * RPM))} g`}
      fill={theme.white} fontFamily={fonts.sans} fontSize={36} position={[cxp, yb - 640]} opacity={0} />
  ) as Txt;

  [xAxis, yAxis, xLab, yLab, noise, noiseLab, curve, dot, readout].forEach(n => view.add(n));

  // bot to the left, axes + noise floor on the right
  yield* all(
    robot.position([-640, 0], 0.9, easeInOutCubic),
    robot.scale(0.85, 0.9, easeInOutCubic),
    xAxis.opacity(1, 0.5), yAxis.opacity(1, 0.5),
    xLab.opacity(1, 0.5), yLab.opacity(1, 0.5),
  );
  yield* all(noise.opacity(0.18, 0.5), noiseLab.opacity(1, 0.5));

  // sweep RPM up: the curve draws out of the noise, bot spins faster alongside
  yield* all(curve.opacity(1, 0.4), dot.opacity(1, 0.4), readout.opacity(1, 0.4));
  yield* all(
    p(1, 4.5, linear),
    robot.rotation(robot.rotation() + 360 * 9, 4.5, linear),
  );
  yield* waitFor(1.4);

  // clear the graph; leave the bot on the left for the next beat (no center bounce)
  yield* all(
    ...[xAxis, yAxis, xLab, yLab, noise, noiseLab, curve, dot, readout].map(n => n.opacity(0, 0.6)),
  );
  [xAxis, yAxis, xLab, yLab, noise, noiseLab, curve, dot, readout].forEach(n => n.remove());
}
