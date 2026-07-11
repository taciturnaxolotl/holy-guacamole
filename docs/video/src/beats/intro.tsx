import {easeOutBack} from '@motion-canvas/core';
import {Stage} from '../lib';

/**
 * BEAT 1 — the melty simply pops onto the stage.
 * No spin-up; we move straight into the heading/arrow beat next.
 */
export function* intro(s: Stage) {
  const {robot} = s;
  yield* robot.scale(1, 0.6, easeOutBack);
}
