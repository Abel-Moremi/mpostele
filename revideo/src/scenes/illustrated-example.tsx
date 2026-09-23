import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Same fixed top-margin anchor band every scene lives in (see
// caption-overlay.tsx's module docstring) - a distinct X slot per component
// type, same convention as title-reveal.tsx (-160) / caption-overlay.tsx (0)
// / outro.tsx (160).
const ANCHOR_Y = -860;
const ANCHOR_X = -80;

// Up to this many items render side by side - composition_validator.py caps
// composition_spec at the same count before a render is ever spawned, so
// this is a rendering-layout constant, not a second source of truth for the
// limit.
const MAX_ITEMS = 3;

export interface IllustratedExampleItem {
	iconId: string;
	caption: string;
}

export interface IllustratedExampleProps {
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	items: IllustratedExampleItem[];
}

interface ItemRefs {
	card: Reference<Rect>;
}

export interface IllustratedExampleRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	items: ItemRefs[];
}

/**
 * Icon files are a small fixed, hand-authored asset library (see
 * revideo/public/design/archetypes/manifest.json) - the agent only ever
 * picks an iconId from that manifest, never invents or draws one (same
 * "choice from a fixed set" boundary app/agents/svg_agent.py already applies
 * to decorations, see that file's module docstring).
 */
const iconSrc = (iconId: string): string => `design/archetypes/${iconId}.svg`;

/** Builds the node tree at rest (hidden) - no animation. Returns refs for
 * play() and for the transitions.ts orchestration in video-project.ts. */
export function mountIllustratedExample(view: Layout, props: IllustratedExampleProps): IllustratedExampleRefs {
	const {backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', items} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);
	const shown = items.slice(0, MAX_ITEMS);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const itemRefs: ItemRefs[] = shown.map(() => ({card: createRef<Rect>()}));

	view.add(
		<Rect ref={root} size={['100%', '100%']} fill={backgroundColor} opacity={0}>
			{/* Faint ruled-paper hairlines - purely decorative texture, drawn
			    directly rather than a new static asset, per design.md's "cream is
			    the page, cream-darker is a hairline" without needing a new token. */}
			{Array.from({length: 7}, (_, i) => (
				<Rect key={`rule-${i}`} width={'100%'} height={2} fill={resolvedTextColor} opacity={0.05} y={-720 + i * 220} />
			))}
			<Rect size={['100%', '100%']} layout direction={'row'} alignItems={'center'} justifyContent={'center'} gap={48} padding={96}>
				{shown.map((item, i) => (
					<Rect
						ref={itemRefs[i].card}
						key={`item-${i}`}
						direction={'column'}
						alignItems={'center'}
						gap={20}
						opacity={0}
						scale={0}
					>
						<Img src={iconSrc(item.iconId)} width={140} />
						<Txt
							text={item.caption}
							fontFamily={fontFamily}
							fontWeight={600}
							fontSize={34}
							fill={resolvedTextColor}
							textAlign={'center'}
							textWrap={true}
							width={260}
						/>
					</Rect>
				))}
			</Rect>
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	return {root, anchor, items: itemRefs};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content.
 * Items pop in one at a time (same easeOutBack overshoot as
 * title-reveal.tsx's headline) rather than all together, so the beat reads
 * as "here's one, and another, and another" instead of one flat reveal. */
export function* playIllustratedExample(
	refs: IllustratedExampleRefs,
	_props: IllustratedExampleProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {items} = refs;
	const perItemSeconds = 0.4;

	for (const {card} of items) {
		yield* all(card().opacity(1, 0.3), card().scale(1, perItemSeconds, easeOutBack));
	}

	const elapsedSeconds = items.length * perItemSeconds;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
