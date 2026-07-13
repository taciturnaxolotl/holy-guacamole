import {Circle, Txt} from '@motion-canvas/2d';
import {createRef, all, waitFor, easeInOutCubic, easeOutCubic} from '@motion-canvas/core';
import {Stage, vector} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 5) — three sensors, and why differencing kills a shove.
 * One accelerometer can't tell the spin's pull from a hit. So we place three:
 * an inner one and two outer ones at different angles. A shove hits all three
 * equally, but the spin's pull differs by radius — so subtracting one sensor
 * from another cancels the shove and leaves only the spin. A third angle
 * recovers which way the shove came from.
 */
export function* sensorShove(s: Stage) {
  const {view, world, robot} = s;
  const est = s.shared.estimate as {opacity: (v: number, t: number) => any} | undefined;
  const readout = s.shared.readout as Txt | undefined;
  const r = robot.bodyRadius();

  // park the drift estimate + error readout while we explain the sensors
  yield* all(
    est ? est.opacity(0, 0.5) : waitFor(0),
    readout ? readout.opacity(0, 0.5) : waitFor(0),
  );

  // three sensors: inner @0°, outer @90°, outer @210°
  const specs = [
    {rad: r * 0.46, deg: 0, label: 'inner'},
    {rad: r * 0.82, deg: 90, label: 'outer'},
    {rad: r * 0.82, deg: 210, label: 'outer'},
  ];
  const pos = specs.map(({rad, deg}) => {
    const a = (deg * Math.PI) / 180;
    return [rad * Math.cos(a), rad * Math.sin(a)] as [number, number];
  });
  const dots = pos.map(p => {
    const dot = (<Circle size={22} fill={theme.yellow} stroke={theme.bg} lineWidth={3} position={p} opacity={0} />) as Circle;
    robot.add(dot);
    return dot;
  });
  s.shared.sensors = dots;
  yield* all(...dots.map(d => d.opacity(1, 0.5)));
  yield* waitFor(5);

  // a shove comes in and knocks the whole bot sideways a touch
  const shoveIn = vector([-460, 0], [-190, 0], theme.red, 12);
  world.add(shoveIn.node);
  yield* shoveIn.ref().end(1, 0.4);
  yield* robot.position([70, 0], 0.5, easeOutCubic);

  // every sensor feels the SAME shove (red), plus its own spin pull (blue, by radius)
  const shoveVecs = pos.map(p => {
    const v = vector([p[0] + 70, p[1]], [p[0] + 70 + 90, p[1]], theme.red, 6);
    world.add(v.node);
    return v;
  });
  yield* all(...shoveVecs.map(v => v.ref().end(1, 0.5)));
  yield* waitFor(0.8);

  const centVecs = pos.map((p, i) => {
    const len = specs[i].rad * 0.7;
    const mag = Math.hypot(p[0], p[1]);
    const dir = [p[0] / mag, p[1] / mag];
    const from: [number, number] = [p[0] + 70, p[1]];
    const to: [number, number] = [from[0] + dir[0] * len, from[1] + dir[1] * len];
    const v = vector(from, to, theme.blue, 6);
    world.add(v.node);
    return v;
  });
  yield* all(...centVecs.map(v => v.ref().end(1, 0.5)));
  yield* waitFor(1);

  // subtract sensors: the identical red shove cancels, leaving only the blue spin
  yield* all(...shoveVecs.map(v => v.ref().opacity(0, 0.7)));
  const cancelTag = (<Txt text={'subtract sensors → the shove cancels'} fill={theme.blue}
    fontFamily={fonts.sans} fontSize={32} position={[0, 380]} opacity={0} />) as Txt;
  view.add(cancelTag);
  yield* cancelTag.opacity(1, 0.6);
  yield* waitFor(1.6);

  // clean up shove furniture; keep the three sensors on the bot
  yield* all(
    cancelTag.opacity(0, 0.6),
    shoveIn.ref().opacity(0, 0.6),
    ...centVecs.map(v => v.ref().opacity(0, 0.6)),
    robot.position(0, 0.8, easeInOutCubic),
  );
  [shoveIn.node, cancelTag, ...shoveVecs.map(v => v.node), ...centVecs.map(v => v.node)]
    .forEach(n => n.remove());
}
