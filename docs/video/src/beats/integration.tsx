import {Circle, Line, Txt} from '@motion-canvas/2d';
import {createSignal, all, waitFor, linear, easeInOutCubic} from '@motion-canvas/core';
import {Stage, tex} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 4c) — heading is the integral of spin rate.
 * Bot spins on the left; on the right, time sweeps forward. ω wobbles a little
 * (real spin isn't perfectly steady); the area under it fills in under a moving
 * cursor, and that running total is θ climbing — its slope steepening and
 * easing with ω. Locked to the bot's own rotation. Ends on θ = ∫ω dt.
 */
export function* integration(s: Stage) {
  const {view, robot} = s;

  // plot on the right, next to the bot
  const x0 = -40, x1 = 780, W = x1 - x0, yb = 300;
  const thMax = 470;
  const TWO = Math.PI * 2, k = 3, hMean = 150, hAmp = 42;
  const t = createSignal(0);

  const X = (u: number) => x0 + u * W;
  const h = (u: number) => hMean + hAmp * Math.sin(TWO * k * u);      // ω height (px)
  const thRaw = (u: number) => hMean * u - (hAmp / (TWO * k)) * (Math.cos(TWO * k * u) - 1);
  const thy = (u: number) => yb - thMax * (thRaw(u) / hMean);         // θ curve y

  const xAxis = (<Line points={[[x0, yb], [x1 + 20, yb]]} stroke={theme.gridLine} lineWidth={3} endArrow arrowSize={12} opacity={0} />) as Line;
  const xLab = (<Txt text={'time'} fill={theme.grey} fontFamily={fonts.sans} fontSize={30} position={[x1 - 10, yb + 44]} opacity={0} />) as Txt;

  // ω: a wobbling spin rate (full curve), with area accumulating beneath it
  const wPts: [number, number][] = [];
  for (let u = 0; u <= 1.0001; u += 0.01) wPts.push([X(u), yb - h(u)]);
  const wLine = (<Line points={wPts} stroke={theme.blue} lineWidth={6} opacity={0} />) as Line;
  const wTag = (<Txt text={'ω  (spin rate)'} fill={theme.blue} fontFamily={fonts.sans} fontSize={30} position={[x0 + 150, yb - hMean - 78]} opacity={0} />) as Txt;

  const areaPts = () => {
    const tt = t();
    const pts: [number, number][] = [];
    for (let u = 0; u <= tt; u += 0.01) pts.push([X(u), yb - h(u)]);
    pts.push([X(tt), yb - h(tt)], [X(tt), yb], [x0, yb]);
    return pts;
  };
  const area = (<Line points={areaPts} closed fill={theme.teal} lineWidth={0} opacity={0} />) as Line;

  // sweeping time cursor
  const cursor = (<Line points={() => [[X(t()), yb + 10], [X(t()), yb - thMax - 20]]} stroke={theme.grey} lineWidth={2} lineDash={[6, 8]} opacity={0} />) as Line;

  // θ: the running total (integral of the wobble), climbing with varying slope
  const thPts = () => {
    const tt = t();
    const pts: [number, number][] = [];
    for (let u = 0; u <= tt; u += 0.01) pts.push([X(u), thy(u)]);
    pts.push([X(tt), thy(tt)]);
    return pts;
  };
  const thLine = (<Line points={thPts} stroke={theme.yellow} lineWidth={6} opacity={0} />) as Line;
  const thTag = (<Txt text={'θ  (heading)'} fill={theme.yellow} fontFamily={fonts.sans} fontSize={30} position={[x1 - 150, yb - thMax + 6]} opacity={0} />) as Txt;
  const thDot = (<Circle size={20} fill={theme.yellow} position={() => [X(t()), thy(t())]} opacity={0} />) as Circle;

  const eq = tex('\\theta = \\displaystyle\\int \\omega \\, dt', {fontSize: 60});
  eq.ref().position([380, -420]);

  [xAxis, xLab, wLine, wTag, area, cursor, thLine, thTag, thDot].forEach(n => view.add(n));
  view.add(eq.node);

  // bot to the left, axes on the right
  yield* all(
    robot.position([-640, 0], 0.9, easeInOutCubic),
    robot.scale(0.85, 0.9, easeInOutCubic),
    xAxis.opacity(1, 0.5), xLab.opacity(1, 0.5),
    wLine.opacity(1, 0.5), wTag.opacity(1, 0.5),
  );

  // sweep time — locked to the bot's spin. area fills, θ climbs by the same amount
  yield* all(
    area.opacity(0.22, 0.4), cursor.opacity(1, 0.4),
    thLine.opacity(1, 0.4), thTag.opacity(1, 0.4), thDot.opacity(1, 0.4),
  );
  yield* all(
    t(1, 8, linear),
    robot.rotation(robot.rotation() + 360 * 4, 8, linear),
    eq.ref().opacity(1, 1),
  );
  yield* waitFor(2.5);

  // clear the graph, recenter the bot
  yield* all(
    robot.position(0, 0.9, easeInOutCubic),
    robot.scale(1, 0.9, easeInOutCubic),
    eq.ref().opacity(0, 0.6),
    ...[xAxis, xLab, wLine, wTag, area, cursor, thLine, thTag, thDot].map(n => n.opacity(0, 0.6)),
  );
  [xAxis, xLab, wLine, wTag, area, cursor, thLine, thTag, thDot, eq.node].forEach(n => n.remove());
}
