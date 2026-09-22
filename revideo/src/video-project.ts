import {Layout, makeScene2D, Rect} from '@revideo/2d';
import {makeProject, Reference, ThreadGenerator, useScene} from '@revideo/core';

import '../global.css';
import {mountCaptionOverlay, playCaptionOverlay, CaptionOverlayRefs} from './scenes/caption-overlay';
import {mountOutro, playOutro, OutroRefs} from './scenes/outro';
import {mountTitleReveal, playTitleReveal, TitleRevealRefs} from './scenes/title-reveal';
import type {Scene} from './schema';
import {fadeIn, runTransition, TRANSITION_SECONDS} from './transitions';

// Keep in sync with app/config/settings.py's REVIDEO_WIDTH/HEIGHT/FPS -
// video_engine.py invokes this project and expects this exact canvas/frame
// rate. TRANSITION_SECONDS (transitions.ts) must likewise stay in sync with
// settings.py's own copy of that constant.
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

interface MountedScene {
	root: Reference<Rect>;
	anchor: Reference<Rect>;
}

/**
 * The only place a scene "component" name (agent-generated data) resolves
 * to actual generator functions (hand-written code). This is what keeps
 * composition_agent.py's output data-only - it picks entries from this
 * fixed table, it never generates code.
 */
function mountScene(view: Layout, scene: Scene): MountedScene {
	switch (scene.component) {
		case 'TitleReveal':
			return mountTitleReveal(view, scene.props);
		case 'CaptionOverlay':
			return mountCaptionOverlay(view, scene.props);
		case 'Outro':
			return mountOutro(view, scene.props);
	}
}

function* playScene(mounted: MountedScene, scene: Scene, headSeconds: number, tailSeconds: number): ThreadGenerator {
	switch (scene.component) {
		case 'TitleReveal':
			yield* playTitleReveal(mounted as TitleRevealRefs, scene.props, scene.durationInFrames, FPS, headSeconds, tailSeconds);
			return;
		case 'CaptionOverlay':
			yield* playCaptionOverlay(mounted as CaptionOverlayRefs, scene.props, scene.durationInFrames, FPS, headSeconds, tailSeconds);
			return;
		case 'Outro':
			yield* playOutro(mounted as OutroRefs, scene.props, scene.durationInFrames, FPS, headSeconds, tailSeconds);
			return;
	}
}

function removeScene(mounted: MountedScene): void {
	mounted.root().remove();
	mounted.anchor().remove();
}

/**
 * Mounts each scene in order, plays its own entrance+hold, then transitions
 * into the next one instead of a hard cut - see transitions.ts. A cut
 * borrows a TRANSITION_SECONDS-long visual overlap from the outgoing
 * scene's own tail (playScene's tailSeconds) - and the very first scene's
 * plain fade-in (there being no outgoing scene to have carved it from) is
 * likewise carved from its OWN head (headSeconds), so total elapsed time
 * still equals the sum of every scene's durationInFrames exactly, same as
 * before any of this existed - composition_agent.py's real-narration-length
 * timing (see its module docstring) is unaffected by this file.
 */
const video = makeScene2D('video', function* (view) {
	const scenes = useScene().variables.get('scenes', [] as Scene[])() as Scene[];

	let current = mountScene(view, scenes[0]);
	yield* fadeIn(current, TRANSITION_SECONDS);

	for (let i = 0; i < scenes.length; i++) {
		const scene = scenes[i];
		const isFirst = i === 0;
		const isLast = i === scenes.length - 1;
		const headSeconds = isFirst ? TRANSITION_SECONDS : 0;
		const tailSeconds = isLast ? 0 : TRANSITION_SECONDS;

		yield* playScene(current, scene, headSeconds, tailSeconds);

		if (isLast) {
			break;
		}
		const next = mountScene(view, scenes[i + 1]);
		yield* runTransition(scene.transitionOut ?? 'crossfade', current, next, TRANSITION_SECONDS);
		removeScene(current);
		current = next;
	}

	removeScene(current);
});

export default makeProject({
	scenes: [video],
	settings: {
		shared: {
			size: {x: WIDTH, y: HEIGHT},
		},
		rendering: {
			fps: FPS,
			exporter: {
				name: '@revideo/core/ffmpeg',
				options: {format: 'mp4'},
			},
		},
	},
});
