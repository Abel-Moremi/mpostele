import {Circle, Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Same fixed top-margin anchor band every scene lives in (see
// caption-overlay.tsx's module docstring) - a distinct X slot per component
// type, same convention as the other scenes.
const ANCHOR_Y = -860;
const ANCHOR_X = -40;

// Same cap as illustrated-example.tsx - composition_validator.py enforces
// this before a render is spawned, this is only the layout-side mirror.
const MAX_ITEMS = 3;
const CIRCLE_DIAMETER = 200;

export interface BadgeChecklistItem {
	iconId: string;
	caption: string;
}

export interface BadgeChecklistProps {
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	confirmColor?: string;
	items: BadgeChecklistItem[];
}

interface ItemRefs {
	card: Reference<Rect>;
	check: Reference<Circle>;
}

export interface BadgeChecklistRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	stamp: Reference<Rect>;
	items: ItemRefs[];
}

const iconSrc = (iconId: string): string => `design/archetypes/${iconId}.svg`;

/**
 * The "everything's included" payoff beat - deliberately reuses the exact
 * same items composition_agent.py already chose for IllustratedExample
 * (same iconId/caption pairs), just restyled as confirmation badges, so the
 * characters introduced early in the video pay off again here instead of
 * being shown once and dropped (see that file's own module docstring for
 * why icons are a fixed hand-authored set, never agent-drawn).
 */
export function mountBadgeChecklist(view: Layout, props: BadgeChecklistProps): BadgeChecklistRefs {
	const {backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', confirmColor, items} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);
	const check = confirmColor ?? accentColor;
	const shown = items.slice(0, MAX_ITEMS);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	const stamp = createRef<Rect>();
	const itemRefs: ItemRefs[] = shown.map(() => ({card: createRef<Rect>(), check: createRef<Circle>()}));

	view.add(
		<Rect
			ref={root}
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			gap={80}
			padding={96}
			opacity={0}
		>
			<Rect direction={'row'} alignItems={'center'} justifyContent={'center'} gap={56}>
				{shown.map((item, i) => (
					<Rect ref={itemRefs[i].card} key={`badge-${i}`} direction={'column'} alignItems={'center'} gap={20} opacity={0} scale={0}>
						{/* No `layout` on this wrapper - the circle, icon and
						    checkmark all stack concentrically at (0,0), the
						    same "absolute, not flex" trick abstract-transition.tsx
						    uses for its orb + orbit group. */}
						<Rect width={CIRCLE_DIAMETER} height={CIRCLE_DIAMETER}>
							<Circle width={CIRCLE_DIAMETER} height={CIRCLE_DIAMETER} fill={accentColor} opacity={0.14} />
							<Img src={iconSrc(item.iconId)} width={CIRCLE_DIAMETER * 0.5} />
							<Circle ref={itemRefs[i].check} width={44} height={44} fill={check} x={CIRCLE_DIAMETER * 0.32} y={CIRCLE_DIAMETER * 0.32} scale={0}>
								<Txt text={'✓'} fontFamily={fontFamily} fontWeight={700} fontSize={26} fill={'#FFFFFF'} />
							</Circle>
						</Rect>
						<Txt
							text={item.caption}
							fontFamily={fontFamily}
							fontWeight={600}
							fontSize={30}
							fill={resolvedTextColor}
							textAlign={'center'}
							textWrap={true}
							width={220}
						/>
					</Rect>
				))}
			</Rect>
			<Rect
				ref={stamp}
				stroke={accentColor}
				lineWidth={3}
				lineDash={[10, 7]}
				radius={16}
				padding={[14, 28]}
				rotation={-4}
				opacity={0}
			>
				<Txt text={'Included'} fontFamily={fontFamily} fontStyle={'italic'} fontWeight={700} fontSize={34} fill={accentColor} />
			</Rect>
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	return {root, anchor, stamp, items: itemRefs};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content.
 * Badges pop in one at a time (same stagger as illustrated-example.tsx),
 * each immediately followed by its own checkmark landing, then the stamp
 * drops in once every badge has confirmed. */
export function* playBadgeChecklist(
	refs: BadgeChecklistRefs,
	_props: BadgeChecklistProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {items, stamp} = refs;
	const perItemSeconds = 0.35;
	const checkSeconds = 0.25;

	for (const {card, check} of items) {
		yield* all(card().opacity(1, 0.25), card().scale(1, perItemSeconds, easeOutBack));
		yield* check().scale(1, checkSeconds, easeOutBack);
	}
	yield* stamp().opacity(1, 0.3);

	const elapsedSeconds = items.length * (perItemSeconds + checkSeconds) + 0.3;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
