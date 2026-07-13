import { Circle } from "@motion-canvas/2d";
import { all, linear, waitFor, easeInOutCubic } from "@motion-canvas/core";
import { Stage, vector, settleRotation } from "../lib";
import { theme } from "../theme";

/**
 * BEAT 4 — how it actually travels.
 * A pale guide shows the goal direction. Each revolution, at the instant the
 * body's heading lines up with the goal, a red thrust pulse fires and the
 * robot nudges over. Little kicks add up to a straight glide — the trail
 * dots make the accumulation legible.
 */
export function* translation(s: Stage) {
	const { world, robot } = s;

	yield* robot.rotation(settleRotation(robot.rotation()), 0.8, easeInOutCubic);

	const guide = vector([0, 0], [560, 0], theme.gridLine, 4);
	world.add(guide.node);

	yield* guide.ref().end(1, 0.8);

	const trail: Circle[] = [];
	const step = 78; // how far the robot moves per kick
	for (let i = 0; i < 4; i++) {
		const at = robot.position();

		const dot = (
			<Circle size={10} fill={theme.blueLight} position={at} opacity={0} />
		) as Circle;
		world.add(dot);
		trail.push(dot);

		// kick arrow spans exactly the distance travelled this step
		const pulse = vector([at.x, at.y], [at.x + step, at.y], theme.red, 8);
		world.add(pulse.node);

		// first the kick arrow extends...
		yield* pulse.ref().end(1, 0.3);
		yield* waitFor(0.4);
		// ...then drift first, then spin — so the nudge reads clearly before the turn
		yield* all(
			robot.position.x(at.x + step, 0.5, easeInOutCubic),
			dot.opacity(0.75, 0.2),
			pulse.ref().opacity(0, 0.4),
		);
		yield* robot.rotation(robot.rotation() + 360, 0.8, linear);
		pulse.node.remove();
	}

	yield* waitFor(0.3);
	yield* guide.ref().opacity(0, 0.8);
	guide.node.remove();

	// glide back to center; sweep the trail away
	yield* all(
		robot.position.x(0, 1.4, easeInOutCubic),
		...trail.map((d) => d.opacity(0, 0.8)),
	);
	trail.forEach((d) => d.remove());
}
