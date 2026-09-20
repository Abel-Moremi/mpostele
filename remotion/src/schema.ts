import {z} from 'zod';

// Node-side half of the composition-spec validation boundary. Keep this in
// sync with app/agents/composition_validator.py's ALLOWED_COMPONENTS /
// REQUIRED_PROPS and app/agents/composition_agent.py's PROMPT - the Python
// side validates before a render is even spawned, this schema is the last
// check before the scene data reaches React.
//
// fontFamily/textColor/logoSrc fields are optional brand overrides (see
// remotion/src/fonts.ts and remotion/public/design/design.md) - components
// fall back to a generic sans-serif font and a computed contrast-safe text
// color (remotion/src/color.ts) when these are omitted, so a differently-
// branded job doesn't need to set them at all and can't render illegible
// text against whatever background color it picks.

const titleRevealScene = z.object({
	component: z.literal('TitleReveal'),
	durationInFrames: z.number().int().positive(),
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
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		textColor: z.string().optional(),
		fontFamily: z.string().optional(),
	}),
});

const outroScene = z.object({
	component: z.literal('Outro'),
	durationInFrames: z.number().int().positive(),
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

export const sceneSchema = z.discriminatedUnion('component', [
	titleRevealScene,
	captionOverlayScene,
	outroScene,
]);

export const compositionPropsSchema = z.object({
	scenes: z.array(sceneSchema).min(1),
});

export type CompositionProps = z.infer<typeof compositionPropsSchema>;
export type Scene = z.infer<typeof sceneSchema>;

// Poster path - keep in sync with app/agents/poster_validator.py's
// REQUIRED_KEYS and app/agents/poster_layout_agent.py's PROMPT.
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

export type PosterProps = z.infer<typeof posterPropsSchema>;
