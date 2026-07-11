import {Circle, Line, Spline, Txt, Node} from '@motion-canvas/2d';
import {createRef, createSignal} from '@motion-canvas/core';
import {all, waitFor, linear, easeInOutCubic, easeOutCubic} from '@motion-canvas/core';
import {Stage, label, settleRotation} from '../lib';
import {theme} from '../theme';

/**
 * BEAT 7 — how an EKF actually works, drawn as the belief it tracks.
 *
 * The filter never stores a single number; it stores a *distribution* — a bell
 * curve over heading whose center is the best guess and whose width is the
 * uncertainty. Every tick it does two things:
 *   PREDICT  — roll the belief forward with the physics; uncertainty grows
 *              (the bell widens).
 *   UPDATE   — multiply that belief by the sensor's (also-uncertain) reading.
 *              The product is a sharper bell sitting between the two.
 * Run it a few times and the belief converges onto the truth and stays sharp,
 * which is exactly the dashed estimate on the robot snapping onto the heading.
 * The "extended" part is just: the sensor curve a = ω²r is nonlinear, so it's
 * replaced by its tangent line at the current guess.
 */
export function* solution(s: Stage) {
  const {view, robot} = s;
  const est = s.shared.estimate as Node;
  const readout = s.shared.readout as Txt | undefined;

  yield* robot.rotation(settleRotation(robot.rotation()), 0.8, easeInOutCubic);
  const truth = robot.rotation();

  // the drift estimate + error readout were parked during the sensor beats;
  // bring them back so we can watch the filter converge them
  yield* all(
    est.opacity(1, 0.5),
    readout ? readout.opacity(1, 0.5) : waitFor(0),
  );

  // slide the robot aside so the belief plot has the stage
  // (the estimate vector rides along with it so it doesn't get left behind)
  yield* all(
    robot.position([-700, 0], 1, easeInOutCubic),
    robot.scale(0.95, 1, easeInOutCubic),
    est.position([-700, 0], 1, easeInOutCubic),
    est.scale(0.95, 1, easeInOutCubic),
  );

  // --- belief plot geometry (screen space) ---------------------------------
  const cx = 250;   // plot center x
  const base = 210; // baseline y (bells rise above; centered on the robot)
  const AMP = 420;  // nominal bell height at the reference width (px)
  const K = 3.6;    // px per value-unit (value ≈ heading degrees off truth)
  const V = 150;    // value half-range plotted
  const REFSIG = 34; // width at which nominal height == drawn height
  const bump = (v: number, mu: number, sig: number, amp: number) =>
    base - amp * Math.exp(-((v - mu) ** 2) / (2 * sig * sig));
  // drawn height conserves area: narrower bell → taller, wider bell → shorter.
  // `amp` is the presence/weight (0 = hidden, AMP = fully shown).
  const heightFor = (sig: number, amp: number) =>
    Math.min((amp * REFSIG) / sig, AMP * 1.5);
  // open curve (the smooth stroke on top)
  const stroke = (mu: number, sig: number, amp: number) => {
    const h = heightFor(sig, amp);
    const pts: [number, number][] = [];
    for (let v = -V; v <= V; v += 8) pts.push([cx + v * K, bump(v, mu, sig, h)]);
    return pts;
  };
  // closed curve down to the axis (the translucent fill under it)
  const fill = (mu: number, sig: number, amp: number): [number, number][] =>
    [[cx - V * K, base], ...stroke(mu, sig, amp), [cx + V * K, base]];

  // prediction (blue) starts biased and wide — our guess is off and unsure
  const muP = createSignal(100);
  const sigP = createSignal(34);
  const ampP = createSignal(0);
  // measurement (yellow) lands near truth, medium width
  const muM = createSignal(0);
  const sigM = createSignal(28);
  const ampM = createSignal(0);
  // posterior (teal) is the normalized product of the two Gaussians
  const ampPost = createSignal(0);
  const postMu = () => {
    const vp = sigP() ** 2, vm = sigM() ** 2;
    return (muP() * vm + muM() * vp) / (vp + vm);
  };
  const postSig = () => {
    const vp = sigP() ** 2, vm = sigM() ** 2;
    return Math.sqrt((vp * vm) / (vp + vm));
  };

  // axis baseline + a short tick below it marking the true heading
  const axis = createRef<Line>();
  const truthLine = createRef<Line>();
  const truthTag = label('true heading', {fill: theme.grey, fontSize: 22});
  view.add(<Line ref={axis} points={[[cx - V * K, base], [cx + V * K, base]]} stroke={theme.gridLine} lineWidth={3} opacity={0} />);
  view.add(<Line ref={truthLine} points={[[cx, base - 4], [cx, base + 34]]} stroke={theme.grey} lineWidth={3} opacity={0} />);
  truthTag.ref().position([cx, base + 60]);
  view.add(truthTag.node);

  // each bell = a translucent fill + a stroke, both driven by the same signals
  // each bell = a translucent fill + a smooth spline stroke, same signals
  const predFill = createRef<Spline>(), predLine = createRef<Spline>();
  const measFill = createRef<Spline>(), measLine = createRef<Spline>();
  const postFill = createRef<Spline>(), postLine = createRef<Spline>();
  view.add(<Spline ref={predFill} points={() => fill(muP(), sigP(), ampP())} fill={theme.blue} lineWidth={0} opacity={0} />);
  view.add(<Spline ref={predLine} points={() => stroke(muP(), sigP(), ampP())} stroke={theme.blue} lineWidth={5} opacity={0} />);
  view.add(<Spline ref={measFill} points={() => fill(muM(), sigM(), ampM())} fill={theme.yellow} lineWidth={0} opacity={0} />);
  view.add(<Spline ref={measLine} points={() => stroke(muM(), sigM(), ampM())} stroke={theme.yellow} lineWidth={5} opacity={0} />);
  view.add(<Spline ref={postFill} points={() => fill(postMu(), postSig(), ampPost())} fill={theme.teal} lineWidth={0} opacity={0} />);
  view.add(<Spline ref={postLine} points={() => stroke(postMu(), postSig(), ampPost())} stroke={theme.teal} lineWidth={6} opacity={0} />);

  yield* all(axis().opacity(1, 0.5), truthLine().opacity(1, 0.5), truthTag.ref().opacity(1, 0.5));
  yield* waitFor(1.4);

  // the prediction bell rises up out of the axis
  yield* all(
    predFill().opacity(0.16, 0.7),
    predLine().opacity(1, 0.7),
    ampP(AMP, 0.9, easeOutCubic),
  );
  yield* waitFor(1.8);

  // link the robot's dashed estimate to the belief's center
  yield* est.rotation(truth + muP(), 0.6, easeInOutCubic);

  // --- run the predict/update loop until the belief is centered on truth ---
  const cycles = 4;
  for (let i = 0; i < cycles; i++) {
    // a noisy measurement bell rises near the truth (last one lands dead-on)
    muM(i === cycles - 1 ? 0 : (Math.random() * 2 - 1) * 9);
    yield* all(
      measFill().opacity(0.16, 0.6),
      measLine().opacity(1, 0.6),
      ampM(AMP, 0.7, easeOutCubic),
    );
    yield* waitFor(0.9);

    // UPDATE: believe both -> sharper belief that sits between them
    yield* all(
      postFill().opacity(0.22, 0.7),
      postLine().opacity(1, 0.7),
      ampPost(AMP, 0.7, easeOutCubic),
      ampP(AMP * 0.42, 0.7), predFill().opacity(0.06, 0.7), predLine().opacity(0.3, 0.7),
      ampM(AMP * 0.42, 0.7), measFill().opacity(0.06, 0.7), measLine().opacity(0.3, 0.7),
      est.rotation(truth + postMu(), 0.7, easeInOutCubic),
    );
    yield* waitFor(1.1);

    // the teal product *becomes* the new blue belief (morph, don't cut)
    const pMu = postMu(), pSig = postSig();
    yield* all(
      muP(pMu, 0.6, easeInOutCubic),
      sigP(pSig, 0.6, easeInOutCubic),
      ampP(AMP, 0.6),
      predFill().opacity(0.16, 0.6),
      predLine().opacity(1, 0.6),
      postFill().opacity(0, 0.5), postLine().opacity(0, 0.5),
      measFill().opacity(0, 0.5), measLine().opacity(0, 0.5),
      ampM(0, 0.5),
    );
    ampPost(0);

    // PREDICT: time passes and the robot drifts, so the belief spreads again
    yield* sigP(Math.min(pSig * 1.9, 34), 0.9, easeInOutCubic);
    yield* waitFor(0.8);
  }

  yield* waitFor(2);

  // bring the robot back and let the now-locked estimate track a real spin
  yield* all(
    robot.position(0, 1, easeInOutCubic),
    robot.scale(1, 1, easeInOutCubic),
    est.position(0, 1, easeInOutCubic),
    est.scale(1, 1, easeInOutCubic),
    est.rotation(truth, 0.8, easeInOutCubic),
    predFill().opacity(0, 0.6),
    predLine().opacity(0, 0.6),
    axis().opacity(0, 0.6),
    truthLine().opacity(0, 0.6),
    truthTag.ref().opacity(0, 0.6),
  );
  yield* all(
    robot.rotation(robot.rotation() + 360 * 2, 2.4, linear),
    est.rotation(est.rotation() + 360 * 2, 2.4, linear),
  );

  // tidy up for the sign-off, keep the robot + heading
  yield* all(
    robot.rotation(settleRotation(robot.rotation()), 1, easeInOutCubic),
    est.rotation(settleRotation(est.rotation()), 1, easeInOutCubic),
    readout ? readout.opacity(0, 0.8) : waitFor(0),
  );
  [predFill(), predLine(), measFill(), measLine(), postFill(), postLine(),
    axis(), truthLine(), truthTag.node, readout].forEach(n => n?.remove());
  est.remove();
}
