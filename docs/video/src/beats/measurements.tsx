import {Txt, Layout} from '@motion-canvas/2d';
import {createRef, all, sequence, waitFor, easeInOutCubic} from '@motion-canvas/core';
import {Stage} from '../lib';
import {theme, fonts} from '../theme';

/**
 * BEAT (script 6) — six measurements, four unknowns.
 * Three sensors each read two axes → six numbers a tick. The physics only has
 * four unknowns (spin rate², angular acceleration, and linear drift in x & y).
 * More equations than unknowns means the readings can check each other — which
 * is what a Kalman filter exploits: predict the next tick, then compare.
 */
export function* measurements(s: Stage) {
  const {view, robot} = s;

  // tuck the bot up top, kept large
  yield* all(
    robot.position([0, -240], 0.9, easeInOutCubic),
    robot.scale(0.82, 0.9, easeInOutCubic),
  );

  const col = (header: string, color: string, rows: string[], x: number) => {
    const ref = createRef<Layout>();
    view.add(
      <Layout ref={ref} direction={'column'} gap={18} alignItems={'center'} position={[x, 200]} opacity={0} layout>
        <Txt text={header} fill={color} fontFamily={fonts.sans} fontWeight={700} fontSize={40} />
        {rows.map(t => (
          <Txt text={t} fill={theme.white} fontFamily={fonts.sans} fontSize={32} />
        ))}
      </Layout>,
    );
    return ref;
  };

  const meas = col('6 measurements', theme.yellow, [
    'sensor A    aₓ , a_y',
    'sensor B    aₓ , a_y',
    'sensor C    aₓ , a_y',
  ], -420);
  const unk = col('4 unknowns', theme.blue, [
    'ω²   spin rate',
    'α    angular accel',
    'aₓ   drift x',
    'a_y   drift y',
  ], 420);

  yield* sequence(0.5, meas().opacity(1, 0.6), unk().opacity(1, 0.6));
  yield* waitFor(2.6);

  // clear the panel, bring the bot back to center
  yield* all(
    robot.position(0, 0.9, easeInOutCubic),
    robot.scale(1, 0.9, easeInOutCubic),
    meas().opacity(0, 0.6),
    unk().opacity(0, 0.6),
  );
  meas().remove();
  unk().remove();
}
