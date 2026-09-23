import {z} from 'zod';

// Plain-JS runtime twin of src/schema.ts, used by render.mjs (a plain Node
// script, not processed by Vite/TS) to keep the same "last check before the
// scene data reaches Revideo" validation boundary. Keep both in sync - see
// src/schema.ts's own header comment for the rest of that boundary's chain.

// Keep in sync with src/transitions.ts's TransitionKind and
// app/agents/composition_agent.py's _TRANSITIONS. Optional and absent on the
// last scene - there's nothing to transition into after it.
const transitionOut = z.enum(['crossfade', 'slide', 'matchCut']).optional();

const titleRevealScene = z.object({
	component: z.literal('TitleReveal'),
	durationInFrames: z.number().int().positive(),
	transitionOut,
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		accentColor: z.string(),
		textColor: z.string().optional(),
		fontFamily: z.string().optional(),
		decorationSrc: z.string().optional(),
	}),
});

const captionOverlayScene = z.object({
	component: z.literal('CaptionOverlay'),
	durationInFrames: z.number().int().positive(),
	transitionOut,
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		accentColor: z.string(),
		textColor: z.string().optional(),
		fontFamily: z.string().optional(),
	}),
});

const outroScene = z.object({
	component: z.literal('Outro'),
	durationInFrames: z.number().int().positive(),
	transitionOut,
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		accentColor: z.string(),
		textColor: z.string().optional(),
		fontFamily: z.string().optional(),
		logoSrc: z.string().optional(),
		decorationSrc: z.string().optional(),
	}),
});

const illustratedExampleScene = z.object({
	component: z.literal('IllustratedExample'),
	durationInFrames: z.number().int().positive(),
	transitionOut,
	props: z.object({
		backgroundColor: z.string(),
		accentColor: z.string(),
		textColor: z.string().optional(),
		fontFamily: z.string().optional(),
		items: z
			.array(z.object({iconId: z.string(), caption: z.string()}))
			.min(1)
			.max(3),
	}),
});

const abstractTransitionScene = z.object({
	component: z.literal('AbstractTransition'),
	durationInFrames: z.number().int().positive(),
	transitionOut,
	props: z.object({
		backgroundColor: z.string(),
		accentColor: z.string(),
		secondaryColor: z.string(),
		tertiaryColor: z.string(),
	}),
});

const sceneSchema = z.discriminatedUnion('component', [
	titleRevealScene,
	captionOverlayScene,
	outroScene,
	illustratedExampleScene,
	abstractTransitionScene,
]);

export const compositionPropsSchema = z.object({
	scenes: z.array(sceneSchema).min(1),
});

export const posterPropsSchema = z.object({
	headline: z.string(),
	ctaText: z.string(),
	backgroundColor: z.string(),
	accentColor: z.string(),
	headlineColor: z.string().optional(),
	ctaTextColor: z.string().optional(),
	headlineFontFamily: z.string().optional(),
	ctaFontFamily: z.string().optional(),
	logoSrc: z.string().optional(),
	decorationSrc: z.string().optional(),
});
