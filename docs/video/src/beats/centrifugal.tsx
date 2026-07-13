import {Circle, Line} from '@motion-canvas/2d';
import {createRef} from '@motion-canvas/core';
import {all, waitFor, easeInOutCubic} from '@motion-canvas/core';
import {Stage, label, vector, tex, zoomTo, resetCamera, settleRotation} from '../lib';
import {theme} from '../theme';

/**
 * BEAT 5 — where heading comes from (the core idea), built as a derivation.
 * Camera glides to a rim sensor. We name the two things we can know — the
 * felt acceleration `a` and the fixed radius `r` — then let the equation
 * assemble and rearrange to spin rate ω. The heading arrow is hidden during
 * this beat so the diagram stays clean; it reappears in the next beat.
 */
export function* centrifugal(s: Stage) {
  const {view, world, robot} = s;
  const heading = s.shared.heading;

  yield* robot.rotation(settleRotation(robot.rotation()), 0.8, easeInOutCubic);
  const r = robot.bodyRadius();

  // hide the heading arrow for the equation scene
  if (heading) yield* heading.opacity(0, 0.4);

  // a sensor out on the rim, then push in on it
  const sensor = (
    <Circle size={20} fill={theme.yellow} stroke={theme.bg} lineWidth={3} position={[r, 0]} opacity={0} />
  ) as Circle;
  robot.add(sensor);
  s.shared.sensor = sensor;

  yield* sensor.opacity(1, 0.5);
  yield* zoomTo(world, [r, 0], 2, 1.6);
  yield* waitFor(0.4);

  // the radius r: distinct color so it reads against the blue accel arrow
  const rLine = createRef<Line>();
  robot.add(
    <Line
      ref={rLine}
      points={[[0, 0], [r, 0]]}
      stroke={theme.green}
      lineWidth={5}
      end={0}
    />,
  );
  const rTag = label('r', {fill: theme.green, fontSize: 36});
  rTag.ref().position([r / 2, 34]);
  robot.add(rTag.node);
  yield* all(rLine().end(1, 0.6), rTag.ref().opacity(1, 0.5));
  yield* waitFor(0.3);

  // the felt acceleration a: same length as the heading arrow for visual consistency
  const aLen = 90;
  const a = vector([r, 0], [r + aLen, 0], theme.blue, 6);
  robot.add(a.node);
  const aTag = label('a', {fill: theme.blue, fontSize: 36});
  aTag.ref().position([r + aLen + 25, -30]);
  robot.add(aTag.node);
  yield* all(a.ref().end(1, 0.7), aTag.ref().opacity(1, 0.5));

  // spin the bot to show what the pull feels like at speed
  yield* robot.rotation(robot.rotation() + 360 * 5, 2.5, easeInOutCubic);
  yield* waitFor(0.5);

  // the derivation, stacked on the right: measure a, then solve for spin rate ω
  const e1 = tex('a = \\omega^2 r', {fontSize: 60});
  const e2 = tex('\\omega^2 = a / r', {fontSize: 60});
  const e3 = tex('\\omega = \\sqrt{\\,a / r\\,}', {fontSize: 60});
  e1.ref().position([620, -110]);
  e2.ref().position([620, 90]);
  e3.ref().position([620, 90]);
  [e1, e2, e3].forEach(e => view.add(e.node));

  yield* e1.ref().opacity(1, 0.7);
  yield* waitFor(4.5);

  // flip it to solve for ω, then morph the square root in
  yield* e2.ref().opacity(1, 0.7);
  yield* waitFor(3);
  yield* all(e2.ref().opacity(0, 0.2), e3.ref().opacity(1, 0.2));
  yield* waitFor(7);

  // pull back out, clear the math and diagram arrows
  yield* all(
    resetCamera(world, 1.4),
    a.ref().opacity(0, 0.8),
    aTag.ref().opacity(0, 0.8),
    rLine().opacity(0, 0.8),
    rTag.ref().opacity(0, 0.8),
    e1.ref().opacity(0, 0.8),
    e3.ref().opacity(0, 0.8),
    sensor.opacity(0, 0.8),
  );
  [a.node, aTag.node, rLine(), rTag.node, e1.node, e2.node, e3.node, sensor]
    .forEach(n => n?.remove());
  s.shared.sensor = undefined;

  // restore the heading arrow for the next beat
  if (heading) yield* heading.opacity(1, 0.4);
}
