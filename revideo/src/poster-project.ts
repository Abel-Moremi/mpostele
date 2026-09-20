import {makeProject, useScene} from '@revideo/core';
import {makeScene2D} from '@revideo/2d';

import '../global.css';
import {poster} from './scenes/poster';
import type {PosterProps} from './schema';

// Keep WIDTH/HEIGHT in sync with app/config/settings.py's
// REVIDEO_WIDTH/HEIGHT - poster_engine.py and video_engine.py's cover-image
// render invoke this project and expect this exact canvas.
const WIDTH = 1080;
const HEIGHT = 1920;

const posterScene = makeScene2D('poster', function* (view) {
	const props = useScene().variables.get('props', {} as PosterProps)() as PosterProps;
	yield* poster(view, props);
});

export default makeProject({
	scenes: [posterScene],
	settings: {
		shared: {
			size: {x: WIDTH, y: HEIGHT},
		},
		rendering: {
			fps: 30,
			exporter: {
				name: '@revideo/core/ffmpeg',
				options: {format: 'mp4'},
			},
		},
	},
});
