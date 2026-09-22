import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Top-margin band every scene's anchor lives in - see caption-overlay.tsx's
// module docstring for why. Distinct from `badge` below, which stays the
// CTA's own flex-centered, self-sized container - the anchor is a separate,
// purely decorative shape dedicated to transition continuity.
const ANCHOR_Y = -860;
const ANCHOR_X = 160;

export interface OutroProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	logoSrc?: string;
	decorationSrc?: string;
}

export interface OutroRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	logo: Reference<Img>;
	badge: Reference<Rect>;
	decoration: Reference<Img>;
}

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountOutro(view: Layout, props: OutroProps): OutroRefs {
	const {text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', logoSrc, decorationSrc} = props;
	const resolvedTextColor = textColor ?? getContrastColor(accentColor);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const logo = createRef<Img>();
	const badge = createRef<Rect>();
	const label = createRef<Txt>();
	const decoration = createRef<Img>();

	view.add(
		<Rect
			ref={root}
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			padding={108}
			gap={40}
			opacity={0}
		>
			{logoSrc && <Img ref={logo} src={logoSrc} width={96} opacity={0} />}
			<Rect ref={badge} fill={accentColor} radius={999} padding={[12, 24]} opacity={0} scale={1}>
				<Txt
					ref={label}
					text={text}
					fontFamily={fontFamily}
					fontWeight={600}
					fontSize={40}
					fill={resolvedTextColor}
					textAlign={'center'}
				/>
			</Rect>
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	if (decorationSrc) {
		view.add(
			<Img ref={decoration} src={decorationSrc} width={100} x={-540 + 48 + 50} y={960 - 48 - 50} opacity={0} />,
		);
	}

	return {root, anchor, logo, badge, decoration};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content. */
export function* playOutro(
	refs: OutroRefs,
	props: OutroProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {logoSrc, decorationSrc} = props;
	const {logo, badge, decoration} = refs;

	yield* all(
		badge().opacity(1, 0.5),
		...(logoSrc ? [logo().opacity(1, 0.5)] : []),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);
	yield* badge().scale(1.06, 0.3, easeOutBack).to(1, 0.3);

	const elapsedSeconds = 1.1;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
