import {waitFor, easeInOutCubic, easeInOutSine} from "@motion-canvas/core";
import {Stage, vector, settleRotation} from "../lib";
import {theme} from "../theme";

/**
 * BEAT 3 — there is no fixed "forward".
 * A yellow heading vector grows out of the hub and is parented to the body,
 * so when the robot turns, "forward" sweeps with it. That's the whole
 * problem stated visually. The vector persists into the next beats.
 */
export function* problem(s: Stage) {
	const {robot} = s;

	yield* robot.rotation(settleRotation(robot.rotation()), 1, easeInOutCubic);

	const head = vector([0, 0], [robot.bodyRadius() + 80, 0], theme.yellow, 7);
	robot.add(head.node);
	s.shared.heading = head.ref();

	yield* head.ref().end(1, 0.8);

	// let the front sweep around to sell the ambiguity (faster)
	yield* robot.rotation(robot.rotation() + 360 * 3, 1.6, easeInOutSine);

	yield* robot.rotation(settleRotation(robot.rotation()), 0.5, easeInOutCubic);
}
