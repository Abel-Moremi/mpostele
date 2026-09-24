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

// Each card's own slot width/gap for manual horizontal placement below -
// matches the caption's own `width` prop, the widest element in a card.
const ITEM_SLOT_WIDTH = 220;
const ITEM_GAP = 56;

/** x offset for the i-th of `count` cards, centered as a group around 0 -
 * see mountBadgeChecklist's own comment for why this is computed by hand
 * rather than a flex row. */
function cardX(i: number, count: number): number {
	const totalWidth = count * ITEM_SLOT_WIDTH + (count - 1) * ITEM_GAP;
	const startX = -(totalWidth - ITEM_SLOT_WIDTH) / 2;
	return startX + i * (ITEM_SLOT_WIDTH + ITEM_GAP);
}

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
			{/* No `layout` on this group wrapper - each card is placed via its
			    own explicit x (cardX), not a flex row. A flex row here was
			    found (empirically) to distort each card's circle into an
			    oval: giving the icon-group wrapper below an explicit size
			    made it a flex row item and un-distorted the row's centering
			    at the cost of squashing the circle; leaving it unsized fixed
			    the circle but threw off the row's own centering instead.
			    Sidestepping the row entirely avoids the tradeoff. */}
			<Rect>
				{shown.map((item, i) => (
					<Rect
						ref={itemRefs[i].card}
						key={`badge-${i}`}
						x={cardX(i, shown.length)}
						direction={'column'}
						alignItems={'center'}
						gap={20}
						opacity={0}
						scale={0}
					>
						{/* No `layout` on this wrapper either - the circle, icon
						    and checkmark all stack concentrically at (0,0), the
						    same "absolute, not flex" trick abstract-transition.tsx
						    uses for its orb + orbit group. */}
						<Rect>
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
							width={ITEM_SLOT_WIDTH}
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
