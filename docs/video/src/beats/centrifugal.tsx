import {Circle, Line} from '@motion-canvas/2d';
import {createRef} from '@motion-canvas/core';
import {all, waitFor, easeInOutCubic} from '@motion-canvas/core';
import {Stage, label, vector, tex, zoomTo, resetCamera, settleRotation} from '../lib';
import {theme, sizes} from '../theme';

/**
 * BEAT 5 — where heading comes from (the core idea), built as a derivation.
 * Camera glides to a rim sensor. We name the two things we can know — the
 * felt acceleration `a` and the fixed radius `r` — then let the equation
 * assemble, rearrange to the spin rate ω, and finally integrate to heading θ.
 * Each line stays on screen so the chain reads as one argument, and the pace
 * leaves room for voiceover.
 */
export function* centrifugal(s: Stage) {
  const {view, world, robot} = s;

  yield* robot.rotation(settleRotation(robot.rotation()), 0.8, easeInOutCubic);
  const r = robot.bodyRadius();

  // a sensor out on the rim, then push in on it
  const sensor = (
    <Circle size={20} fill={theme.yellow} stroke={theme.bg} lineWidth={3} position={[r, 0]} opacity={0} />
  ) as Circle;
  robot.add(sensor);
  s.shared.sensor = sensor;

  yield* sensor.opacity(1, 0.5);
  yield* zoomTo(world, [r, 0], 2, 1.6);
  yield* waitFor(1);

  // the radius r: a fixed, known distance from center to sensor
  const rLine = createRef<Line>();
  world.add(
    <Line
      ref={rLine}
      points={[[0, 0], [r, 0]]}
      stroke={theme.grey}
      lineWidth={4}
      end={0}
    />,
  );
  const rTag = label('r', {fill: theme.grey, fontSize: 36});
  rTag.ref().position([r / 2, 34]);
  world.add(rTag.node);
  yield* all(rLine().end(1, 0.6), rTag.ref().opacity(1, 0.5));
  yield* waitFor(1.2);

  // the felt acceleration a: what the sensor actually reports
  const a = vector([r, 0], [r + 150, 0], theme.blue, 6);
  world.add(a.node);
  const aTag = label('a', {fill: theme.blue, fontSize: 36});
  aTag.ref().position([r + 175, -30]);
  world.add(aTag.node);
  yield* all(a.ref().end(1, 0.7), aTag.ref().opacity(1, 0.5));
  yield* waitFor(1.4);

  // the derivation, stacked on the right: measure a, then solve for spin rate ω
  const e1 = tex('a = \\omega^2 r', {fontSize: 60});
  const e2 = tex('\\omega^2 = a / r', {fontSize: 60});
  const e3 = tex('\\omega = \\sqrt{\\,a / r\\,}', {fontSize: 60});
  e1.ref().position([620, -110]);
  e2.ref().position([620, 90]);
  e3.ref().position([620, 90]);
  [e1, e2, e3].forEach(e => view.add(e.node));

  yield* e1.ref().opacity(1, 0.7);
  yield* waitFor(1.6);

  // flip it to solve for ω, then morph the square root in
  yield* e2.ref().opacity(1, 0.7);
  yield* waitFor(1.4);
  yield* all(e2.ref().opacity(0, 0.5), e3.ref().opacity(1, 0.5));
  yield* waitFor(1.8);

  // pull back out, clear the math, leave sensor A in place
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
}
