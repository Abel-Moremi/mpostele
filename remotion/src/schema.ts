import {z} from 'zod';

// Node-side half of the composition-spec validation boundary. Keep this in
// sync with app/agents/composition_validator.py's ALLOWED_COMPONENTS /
// REQUIRED_PROPS and app/agents/composition_agent.py's PROMPT - the Python
// side validates before a render is even spawned, this schema is the last
// check before the scene data reaches React.

const titleRevealScene = z.object({
	component: z.literal('TitleReveal'),
	durationInFrames: z.number().int().positive(),
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		accentColor: z.string(),
	}),
});

const captionOverlayScene = z.object({
	component: z.literal('CaptionOverlay'),
	durationInFrames: z.number().int().positive(),
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
	}),
});

const outroScene = z.object({
	component: z.literal('Outro'),
	durationInFrames: z.number().int().positive(),
	props: z.object({
		text: z.string(),
		backgroundColor: z.string(),
		accentColor: z.string(),
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
