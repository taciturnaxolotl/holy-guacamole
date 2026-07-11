import {Node, Txt} from '@motion-canvas/2d';
import {all, linear, waitFor, easeInOutCubic} from '@motion-canvas/core';
import {Stage, vector, settleRotation} from '../lib';
import {theme, fonts, sizes} from '../theme';

/**
 * BEAT 6 — why the naive version fails.
 * A dashed "estimate" heading starts locked to the true yellow one, then, as
 * RPM climbs, a running-total integrator falls behind. The gap opens and a
 * live error readout counts up. This sets up why a filter is needed.
 */
export function* drift(s: Stage) {
  const {view, world, robot} = s;

  yield* robot.rotation(settleRotation(robot.rotation()), 0.8, easeInOutCubic);
  const r = robot.bodyRadius();

  // dashed estimate vector, initially aligned with the true heading
  const est = new Node({rotation: robot.rotation()});
  world.add(est);
  const estVec = vector([0, 0], [r + 80, 0], theme.blueLight, 6);
  est.add(estVec.node);
  estVec.ref().lineDash([14, 10]);
  s.shared.estimate = est;

  const readout = (
    <Txt
      text={() => {
        let d = (((robot.rotation() - est.rotation()) % 360) + 360) % 360;
        if (d > 180) d = 360 - d;
        return `heading error: ${d.toFixed(0)}°`;
      }}
      fill={theme.red}
      fontFamily={fonts.sans}
      fontSize={sizes.label}
      position={[0, -380]}
      opacity={0}
    />
  ) as Txt;
  view.add(readout);

  yield* all(estVec.ref().end(1, 0.6), readout.opacity(1, 0.6));

  // spin up; the estimate lags further and further behind
  const start = robot.rotation();
  yield* all(
    robot.rotation(start + 360 * 8, 4, linear),
    est.rotation(start + 360 * 8 - 200, 4, linear),
  );
  yield* waitFor(0.4);

  // settle spin, keep the gap on screen for the fix
  yield* robot.rotation(settleRotation(robot.rotation()), 1, easeInOutCubic);
  s.shared.readout = readout;
}
