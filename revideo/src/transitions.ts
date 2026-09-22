import type {Rect} from '@revideo/2d';
import {all, Reference, ThreadGenerator} from '@revideo/core';

/**
 * Cut-to-cut transitions between the fixed scene generators in
 * revideo/src/scenes/. Keep in sync with schema.ts's transitionOut enum and
 * app/agents/composition_agent.py's _TRANSITIONS - the agent picks a kind
 * per cut (deterministically, not creatively - see composition_agent.py),
 * this module is the only place that knows how to render each one.
 *
 * Every scene mounts its own small accent-colored "anchor" Rect, always at
 * the same fixed position/size *within* a given scene type but different
 * between scene types (see scenes/*.tsx) - added directly to the master
 * view rather than nested in the scene's own flex layout, so its position
 * is known exactly at mount time with no layout-resolution timing to worry
 * about (the same pattern the existing decoration images already use).
 * matchCut uses that to fake a single shape traveling across the cut.
 */
export type TransitionKind = 'crossfade' | 'slide' | 'matchCut';

export interface TransitionSide {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
}

// MUST stay in sync with app/config/settings.py's TRANSITION_SECONDS - this
// doesn't add to a scene's own durationInFrames total, it borrows a brief
// visual overlap from the outgoing scene's own tail (see video-project.ts).
export const TRANSITION_SECONDS = 0.5;

// Matches video-project.ts's WIDTH - slides fully clear the frame.
const SLIDE_DISTANCE = 1080;

export function* runTransition(
	kind: TransitionKind,
	outgoing: TransitionSide,
	incoming: TransitionSide,
	seconds: number = TRANSITION_SECONDS,
): ThreadGenerator {
	if (kind === 'matchCut') {
		yield* matchCutTransition(outgoing, incoming, seconds);
	} else if (kind === 'slide') {
		yield* slideTransition(outgoing, incoming, seconds);
	} else {
		yield* crossfadeTransition(outgoing, incoming, seconds);
	}
}

/** Also used as the very first scene's entrance (no outgoing side). */
export function* fadeIn(incoming: TransitionSide, seconds: number = TRANSITION_SECONDS): ThreadGenerator {
	yield* all(incoming.root().opacity(1, seconds), incoming.anchor().opacity(1, seconds));
}

function* crossfadeTransition(outgoing: TransitionSide, incoming: TransitionSide, seconds: number): ThreadGenerator {
	yield* all(
		outgoing.root().opacity(0, seconds),
		outgoing.anchor().opacity(0, seconds),
		incoming.root().opacity(1, seconds),
		incoming.anchor().opacity(1, seconds),
	);
}

function* slideTransition(outgoing: TransitionSide, incoming: TransitionSide, seconds: number): ThreadGenerator {
	incoming.root().position.x(SLIDE_DISTANCE);
	incoming.root().opacity(1);
	incoming.anchor().position.x(SLIDE_DISTANCE);
	incoming.anchor().opacity(1);

	yield* all(
		outgoing.root().position.x(-SLIDE_DISTANCE, seconds),
		outgoing.anchor().position.x(-SLIDE_DISTANCE, seconds),
		incoming.root().position.x(0, seconds),
		incoming.anchor().position.x(0, seconds),
	);
}

/**
 * The outgoing scene's own anchor travels to the incoming scene's anchor
 * slot (already known at mount time - read before this starts) while the
 * root content underneath does a plain crossfade. The incoming anchor stays
 * hidden until the travelling shape arrives, then an instant, imperceptible
 * swap hands off to it - two real nodes standing in for what reads on
 * screen as one continuous shape.
 */
function* matchCutTransition(outgoing: TransitionSide, incoming: TransitionSide, seconds: number): ThreadGenerator {
	const targetPosition = incoming.anchor().position();
	const targetSize = incoming.anchor().size();
	const targetFill = incoming.anchor().fill();
	incoming.anchor().opacity(0);

	yield* all(
		outgoing.root().opacity(0, seconds),
		incoming.root().opacity(1, seconds),
		outgoing.anchor().position(targetPosition, seconds),
		outgoing.anchor().size(targetSize, seconds),
		outgoing.anchor().fill(targetFill, seconds),
	);

	incoming.anchor().opacity(1);
	outgoing.anchor().opacity(0);
}
