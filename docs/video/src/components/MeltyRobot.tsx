import {Node, NodeProps, Circle, Rect, initial, signal} from '@motion-canvas/2d';
import {SignalValue, SimpleSignal} from '@motion-canvas/core';
import {theme} from '../theme';

export interface MeltyRobotProps extends NodeProps {
  bodyRadius?: SignalValue<number>;
}

/**
 * A meltybrain drawn the 3b1b way: a thin bright-blue ring, a small center
 * dot, and two short weapon marks on the spin axis. Deliberately minimal so
 * it reads as a diagram, not an illustration.
 *
 * Spin it with `.rotation`. Sub-parts are exposed as refs so beats can
 * highlight the tabs, fade the wheels, or draw off the rim.
 */
export class MeltyRobot extends Node {
  @initial(140)
  @signal()
  public declare readonly bodyRadius: SimpleSignal<number, this>;

  public readonly ring = new Circle({});
  public readonly hub = new Circle({});

  public constructor(props?: MeltyRobotProps) {
    super({...props});
    const r = this.bodyRadius();

    // body ring
    this.ring.size(r * 2);
    this.ring.stroke(theme.blue);
    this.ring.lineWidth(4);
    this.ring.fill(null);
    this.add(this.ring);

    // two weapon tabs on the vertical (spin) axis, as outward-pointing triangles
    // two wheels straddling the ring at top & bottom, so "forward" (+x)
    // points cleanly between them. Chunky rounded rects read as tyres.
    for (const dir of [-1, 1]) {
      this.add(
        <Rect
          y={dir * r}
          width={78}
          height={30}
          radius={10}
          fill={theme.grey}
        />,
      );
    }

    // center hub dot
    this.hub.size(16);
    this.hub.fill(theme.blueLight);
    this.add(this.hub);
  }
}
