import {Circle, Gradient, Layout, Rect} from '@revideo/2d';
import {all, createRef, linear, Reference, ThreadGenerator, waitFor} from '@revideo/core';

// Same fixed top-margin anchor band every scene lives in (see
// caption-overlay.tsx's module docstring) - a distinct X slot per component
// type, same convention as title-reveal.tsx (-160) / caption-overlay.tsx (0)
// / outro.tsx (160) / illustrated-example.tsx (-80).
const ANCHOR_Y = -860;
const ANCHOR_X = 80;

const ORB_DIAMETER = 380;

export interface AbstractTransitionProps {
	backgroundColor: string;
	accentColor: string;
	secondaryColor: string;
	tertiaryColor: string;
}

export interface AbstractTransitionRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	orb: Reference<Circle>;
	orbitGroup: Reference<Rect>;
	gradient: Gradient;
}

/**
 * A brief, textless "something is happening" beat - a glowing orb whose
 * gradient sweeps through the brand's three accent tones plus a few small
 * dots orbiting it, standing in for a literal progress spinner between a
 * content beat and the reveal that follows it (e.g. the last CaptionOverlay
 * and Outro - see composition_agent.py's _build_scenes). Every color here is
 * a fixed brand tone (accentColor/secondaryColor/tertiaryColor), never an
 * LLM-invented hex, same as every other scene's _apply_brand pass.
 */
export function mountAbstractTransition(view: Layout, props: AbstractTransitionProps): AbstractTransitionRefs {
	const {backgroundColor, accentColor, secondaryColor, tertiaryColor} = props;

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const orb = createRef<Circle>();
	const orbitGroup = createRef<Rect>();

	const gradient = new Gradient({
		type: 'conic',
		angle: 0,
		stops: [
			{offset: 0, color: accentColor},
			{offset: 0.33, color: secondaryColor},
			{offset: 0.66, color: tertiaryColor},
			{offset: 1, color: accentColor},
		],
	});

	view.add(
		// No `layout` here deliberately: the orb and orbitGroup must sit
		// concentrically on top of each other, not side by side as flex
		// siblings - both default to x=0/y=0, which is the view's own
		// center (see ANCHOR_X/Y above being offsets from that same origin),
		// so plain absolute positioning is what actually centers them.
		<Rect ref={root} size={['100%', '100%']} fill={backgroundColor} opacity={0}>
			<Circle
				ref={orb}
				width={ORB_DIAMETER}
				height={ORB_DIAMETER}
				fill={gradient}
				shadowColor={accentColor}
				shadowBlur={90}
				scale={0}
				opacity={0}
			/>
			<Rect ref={orbitGroup} opacity={0}>
				<Circle x={0} y={-170} width={12} height={12} fill={accentColor} />
				<Circle x={150} y={90} width={9} height={9} fill={secondaryColor} />
				<Circle x={-145} y={100} width={9} height={9} fill={tertiaryColor} />
				<Circle x={95} y={-150} width={7} height={7} fill={secondaryColor} />
			</Rect>
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	return {root, anchor, orb, orbitGroup, gradient};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content. */
export function* playAbstractTransition(
	refs: AbstractTransitionRefs,
	_props: AbstractTransitionProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {orb, orbitGroup, gradient} = refs;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;

	yield* all(orb().opacity(1, 0.35), orb().scale(1, 0.4), orbitGroup().opacity(1, 0.4));

	const remainingSeconds = Math.max(totalSeconds - 0.4, 0.1);
	yield* all(
		gradient.angle(360, remainingSeconds, linear),
		orbitGroup().rotation(120, remainingSeconds, linear),
		orb().scale(1.05, remainingSeconds / 2).to(1, remainingSeconds / 2),
	);

	if (totalSeconds <= 0.4) {
		yield* waitFor(0);
	}
}
