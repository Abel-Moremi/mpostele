import {makeProject, useScene} from '@revideo/core';
import {makeScene2D} from '@revideo/2d';

import '../global.css';
import {titleReveal} from './scenes/title-reveal';
import {captionOverlay} from './scenes/caption-overlay';
import {outro} from './scenes/outro';
import type {Scene} from './schema';

// Keep WIDTH/HEIGHT/FPS in sync with app/config/settings.py's
// REVIDEO_WIDTH/HEIGHT/FPS - video_engine.py invokes this project and
// expects this exact canvas/frame rate.
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

/**
 * The only place a scene "component" name (agent-generated data) resolves
 * to an actual generator function (hand-written code). This is what keeps
 * composition_agent.py's output data-only - it picks entries from this
 * fixed table, it never generates code. Mirrors
 * remotion/src/MainComposition.tsx's renderScene switch exactly.
 */
const video = makeScene2D('video', function* (view) {
	const scenes = useScene().variables.get('scenes', [] as Scene[])() as Scene[];

	for (const scene of scenes) {
		switch (scene.component) {
			case 'TitleReveal':
				yield* titleReveal(view, scene.props, scene.durationInFrames, FPS);
				break;
			case 'CaptionOverlay':
				yield* captionOverlay(view, scene.props, scene.durationInFrames, FPS);
				break;
			case 'Outro':
				yield* outro(view, scene.props, scene.durationInFrames, FPS);
				break;
		}
	}
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
