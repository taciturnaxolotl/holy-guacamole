import {makeScene2D} from '@motion-canvas/2d';
import {createStage} from '../lib';
import {theme} from '../theme';

import {intro} from '../beats/intro';
import {problem} from '../beats/problem';
import {translation} from '../beats/translation';
import {gyroRedline} from '../beats/gyroRedline';
import {centrifugal} from '../beats/centrifugal';
import {gForce} from '../beats/gForce';
import {integration} from '../beats/integration';
import {drift} from '../beats/drift';
import {sensorShove} from '../beats/sensorShove';
import {measurements} from '../beats/measurements';
import {solution} from '../beats/solution';

/**
 * The entire explainer is ONE continuous scene. Beats hand the same robot and
 * world off to each other so the camera and objects flow without cuts — the
 * 3Blue1Brown feel. Order follows the script (docs/script.md). Pace is loose
 * on purpose; voiceover drives final timing.
 */
export default makeScene2D(function* (view) {
  view.fill(theme.bg);
  const stage = createStage(view);

  yield* intro(stage);        // melty pops in
  yield* problem(stage);      // no constant forward (heading arrow sweeps)
  yield* translation(stage);  // kick once per rotation to drift
  yield* gyroRedline(stage);  // gyros max out → use accelerometers
  yield* centrifugal(stage);  // a = ω²r → ω = √(a/r)
  yield* gForce(stage);       // g grows with rpm² (signal vs noise)
  yield* integration(stage);  // θ = ∫ω dt
  yield* drift(stage);        // integrated error → heading drift
  yield* sensorShove(stage);  // 3 sensors; differencing cancels a shove
  yield* measurements(stage); // 6 measurements, 4 unknowns
  yield* solution(stage);     // EKF fuses them; belief hones in
});
