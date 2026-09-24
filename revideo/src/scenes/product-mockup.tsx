import {Circle, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, Reference, ThreadGenerator, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

// Same fixed top-margin anchor band every scene lives in (see
// caption-overlay.tsx's module docstring) - a distinct X slot per component
// type, same convention as the other scenes.
const ANCHOR_Y = -860;
const ANCHOR_X = 40;

// Same cap as illustrated-example.tsx/badge-checklist.tsx.
const MAX_CHIPS = 3;

// Traffic-light dot colors - fixed decorative chrome (the mockup's window
// frame), not brand-driven data, same status as the "STEP ONE" eyebrow copy
// and window title below.
const TRAFFIC_LIGHT_COLORS = ['#E5847B', '#E5C97B', '#8FAE86'];

export interface ProductMockupItem {
	iconId: string;
	caption: string;
}

export interface ProductMockupProps {
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	headline: string;
	typedText: string;
	items: ProductMockupItem[];
}

interface ChipRefs {
	chip: Reference<Rect>;
}

export interface ProductMockupRefs {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
	card: Reference<Rect>;
	typed: Reference<Txt>;
	chips: ChipRefs[];
	cta: Reference<Rect>;
}

/**
 * A stylized product-UI mockup: a browser-chrome window with a headline, a
 * text input, and chip pills that light up in sequence after it - the same
 * "example" items IllustratedExample and BadgeChecklist already used, paid
 * off a third time here as the literal sentence shown in the input (see
 * composition_agent.py's _build_typed_text). No agent-drawn UI - only
 * headline/typedText/items are data, everything else (window chrome, step
 * eyebrow, CTA chrome) is fixed, hand-written layout. See playProductMockup
 * below for why the input text isn't typed on character-by-character.
 */
export function mountProductMockup(view: Layout, props: ProductMockupProps): ProductMockupRefs {
	const {backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', headline, items} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);
	const shown = items.slice(0, MAX_CHIPS);

	const root = createRef<Rect>();
	const anchor = createRef<Rect>();
	// Named "card", not "window" - this renders inside a real browser page
	// (headless Chromium), where `window` is the global Window object.
	const card = createRef<Rect>();
	const typed = createRef<Txt>();
	const chipRefs: ChipRefs[] = shown.map(() => ({chip: createRef<Rect>()}));
	const cta = createRef<Rect>();

	view.add(
		<Rect ref={root} size={['100%', '100%']} fill={backgroundColor} layout alignItems={'center'} justifyContent={'center'} padding={72} opacity={0}>
			<Rect
				ref={card}
				direction={'column'}
				width={900}
				fill={'#FFFFFF'}
				radius={28}
				shadowColor={'#00000030'}
				shadowBlur={40}
				shadowOffsetY={16}
				scale={0.92}
				opacity={0}
			>
				{/* Title bar */}
				<Rect direction={'row'} alignItems={'center'} gap={10} padding={[18, 28]}>
					{TRAFFIC_LIGHT_COLORS.map((color, i) => (
						<Circle key={`dot-${i}`} width={14} height={14} fill={color} />
					))}
					<Rect grow={1} justifyContent={'center'}>
						<Txt text={'Dreamcraftr · new story'} fontFamily={fontFamily} fontWeight={600} fontSize={20} fill={'#8A8378'} textAlign={'center'} />
					</Rect>
				</Rect>
				<Rect direction={'column'} gap={28} padding={[8, 56, 56, 56]}>
					<Txt text={'STEP ONE · THE IDEA'} fontFamily={fontFamily} fontWeight={600} fontSize={18} letterSpacing={2.5} fill={accentColor} />
					<Txt text={headline} fontFamily={fontFamily} fontWeight={700} fontSize={44} fill={resolvedTextColor} />
					{/* Fixed height (2 lines' worth) rather than auto-sizing to
					    content - the typed text grows character by character
					    during playProductMockup's typing tween; letting this box
					    reflow live was suspected of invalidating the chip/CTA
					    refs below it, though fixing the height alone did not
					    turn out to be the actual fix - kept anyway since it's
					    still the more correct, stable layout regardless. */}
					<Rect fill={'#F7F3EC'} radius={16} padding={[26, 30]} height={140}>
						<Txt ref={typed} text={''} fontFamily={fontFamily} fontWeight={500} fontSize={30} fill={resolvedTextColor} textWrap={true} width={780} />
					</Rect>
					<Rect direction={'row'} gap={16}>
						{shown.map((item, i) => (
							<Rect ref={chipRefs[i].chip} key={`chip-${i}`} fill={'#F7F3EC'} radius={999} padding={[12, 24]} opacity={0.5}>
								<Txt text={item.caption} fontFamily={fontFamily} fontWeight={600} fontSize={24} fill={resolvedTextColor} />
							</Rect>
						))}
					</Rect>
					<Rect ref={cta} fill={'#2B2018'} radius={999} padding={[18, 32]} opacity={0} alignSelf={'start'}>
						<Txt text={'✦  Dream it  →'} fontFamily={fontFamily} fontWeight={600} fontSize={26} fill={'#FFFFFF'} />
					</Rect>
				</Rect>
			</Rect>
		</Rect>,
	);

	view.add(<Rect ref={anchor} width={64} height={8} radius={4} fill={accentColor} x={ANCHOR_X} y={ANCHOR_Y} opacity={0} />);

	return {root, anchor, card, typed, chips: chipRefs, cta};
}

/** Entrance animation + hold. root/anchor visibility is owned by
 * transitions.ts, not here - this only animates this scene's own content.
 * The card scales in, the input text appears, then each chip lights up in
 * a quick sequential stagger, then the CTA pill lands last - mirroring the
 * reference video's "chips fill in, then the button appears" beat.
 *
 * The input text is set instantly rather than typed on character-by-
 * character via Txt's native text tween. That tween was tried first (the
 * same mechanism caption-overlay.tsx uses successfully) and, empirically,
 * broke every yield* after it in this generator: the chip/cta tweens below
 * would run with no thrown error and produce no visible change at all.
 * Re-setting the same text value again right before the final hold is the
 * other half of the workaround - removing either half reproduces the bug.
 * Root cause not confirmed (suspected to be a layout-settling race in this
 * Txt's textWrap reflow, not a scheduling issue - a plain, untweened
 * property set has the same problem, only a tween's setup differs), so
 * this trades the nicer typewriter effect for a mechanism that reliably
 * shows the result at all. */
export function* playProductMockup(
	refs: ProductMockupRefs,
	props: ProductMockupProps,
	durationInFrames: number,
	fps: number,
	headSeconds: number,
	tailSeconds: number,
): ThreadGenerator {
	const {typedText, items} = props;
	const {card, typed, chips, cta} = refs;
	const shown = chips.slice(0, items.length);

	yield* all(card().opacity(1, 0.4), card().scale(1, 0.5, easeOutBack));

	typed().text(typedText);
	const readSeconds = 0.4;
	yield* waitFor(readSeconds);

	const chipSeconds = 0.15;
	for (const {chip} of shown) {
		yield* chip().opacity(1, chipSeconds);
	}
	yield* cta().opacity(1, 0.3);
	typed().text(typedText);

	const elapsedSeconds = 0.5 + readSeconds + shown.length * chipSeconds + 0.3;
	const totalSeconds = durationInFrames / fps - headSeconds - tailSeconds;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}
}
