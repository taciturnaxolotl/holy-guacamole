import {View2D, Node, Latex, Txt, Line} from '@motion-canvas/2d';
import {
  Vector2,
  PossibleVector2,
  createRef,
  Reference,
  ThreadGenerator,
  all,
  easeInOutCubic,
} from '@motion-canvas/core';
import {MeltyRobot} from './components/MeltyRobot';
import {theme, fonts, sizes} from './theme';

/**
 * The whole video lives in one scene. `world` is a single persistent,
 * camera-able container; beats add and transform nodes inside it instead of
 * cutting to fresh scenes. That continuity is the whole 3b1b feel.
 */
export interface Stage {
  view: View2D;
  world: Node;
  robot: MeltyRobot;
  /** handoff bag: objects one beat creates and a later beat keeps animating. */
  shared: Record<string, any>;
}

export function createStage(view: View2D): Stage {
  const world = new Node({});
  const robot = new MeltyRobot({scale: 0});
  world.add(robot);
  view.add(world);
  return {view, world, robot, shared: {}};
}

/** Animate rotation to the nearest upright multiple of 360°, plus extra turns. */
export function settleRotation(current: number, extraTurns = 0): number {
  return Math.ceil(current / 360) * 360 + extraTurns * 360;
}

/** Glide the camera so `focus` (world coords) sits centered at `scale`. */
export function* zoomTo(
  world: Node,
  focus: PossibleVector2,
  scale: number,
  duration: number,
): ThreadGenerator {
  const f = new Vector2(focus);
  yield* all(
    world.scale(scale, duration, easeInOutCubic),
    world.position([-f.x * scale, -f.y * scale], duration, easeInOutCubic),
  );
}

/** Reset the camera to the identity framing. */
export function* resetCamera(world: Node, duration = 1): ThreadGenerator {
  yield* all(
    world.scale(1, duration, easeInOutCubic),
    world.position(0, duration, easeInOutCubic),
  );
}

/** A LaTeX block in the standard white math ink. */
export function tex(
  input: string,
  props: Partial<{fill: string; fontSize: number}> = {},
): {node: Latex; ref: Reference<Latex>} {
  const ref = createRef<Latex>();
  const node = (
    <Latex
      ref={ref}
      tex={input}
      fill={props.fill ?? theme.white}
      fontSize={props.fontSize ?? sizes.body}
      opacity={0}
    />
  ) as Latex;
  return {node, ref};
}

/** A plain caption line (serif body ink). */
export function label(
  text: string,
  props: Partial<{fill: string; fontSize: number; family: string}> = {},
): {node: Txt; ref: Reference<Txt>} {
  const ref = createRef<Txt>();
  const node = (
    <Txt
      ref={ref}
      text={text}
      fill={props.fill ?? theme.white}
      fontFamily={props.family ?? fonts.body}
      fontSize={props.fontSize ?? sizes.body}
      opacity={0}
    />
  ) as Txt;
  return {node, ref};
}

/**
 * A vector arrow from `from` to `to`. Returns the Line with `end` at 0 so
 * beats can "draw" it on by tweening `.end(1)`.
 */
export function vector(
  from: PossibleVector2,
  to: PossibleVector2,
  color = theme.yellow,
  width = 6,
): {node: Line; ref: Reference<Line>} {
  const ref = createRef<Line>();
  const node = (
    <Line
      ref={ref}
      points={[from, to]}
      stroke={color}
      lineWidth={width}
      endArrow
      arrowSize={16}
      end={0}
    />
  ) as Line;
  return {node, ref};
}
