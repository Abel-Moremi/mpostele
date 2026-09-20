import React from 'react';
import {Composition, Still} from 'remotion';
import {MainComposition} from './MainComposition';
import {Poster} from './scenes/Poster';
import {compositionPropsSchema, posterPropsSchema, type CompositionProps, type PosterProps} from './schema';

// Keep WIDTH/HEIGHT/FPS and both composition ids in sync with
// app/config/settings.py's REMOTION_WIDTH/HEIGHT/FPS/COMPOSITION_ID/
// POSTER_COMPOSITION_ID - video_engine.py and poster_engine.py invoke these
// compositions by id and expect this exact canvas/frame rate.
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

const defaultVideoProps: CompositionProps = {
	scenes: [
		{
			component: 'TitleReveal',
			durationInFrames: 60,
			props: {text: 'Default Title', backgroundColor: '#0B1220', accentColor: '#2563EB'},
		},
	],
};

const defaultPosterProps: PosterProps = {
	headline: 'Default Headline',
	ctaText: 'Learn More',
	backgroundColor: '#0B1220',
	accentColor: '#2563EB',
};

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="MainComposition"
				component={MainComposition}
				fps={FPS}
				width={WIDTH}
				height={HEIGHT}
				durationInFrames={defaultVideoProps.scenes.reduce((sum, s) => sum + s.durationInFrames, 0)}
				schema={compositionPropsSchema}
				defaultProps={defaultVideoProps}
				calculateMetadata={async ({props}) => ({
					durationInFrames: props.scenes.reduce((sum, s) => sum + s.durationInFrames, 0),
				})}
			/>
			<Still
				id="Poster"
				component={Poster}
				width={WIDTH}
				height={HEIGHT}
				schema={posterPropsSchema}
				defaultProps={defaultPosterProps}
			/>
		</>
	);
};
