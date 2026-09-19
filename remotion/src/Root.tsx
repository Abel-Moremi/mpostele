import React from 'react';
import {Composition} from 'remotion';
import {MainComposition} from './MainComposition';
import {compositionPropsSchema, type CompositionProps} from './schema';

// Keep WIDTH/HEIGHT/FPS and the composition id in sync with
// app/config/settings.py's REMOTION_WIDTH/HEIGHT/FPS/COMPOSITION_ID -
// remotion_engine.py invokes this composition by that id and expects this
// exact canvas/frame rate.
const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

const defaultProps: CompositionProps = {
	scenes: [
		{
			component: 'TitleReveal',
			durationInFrames: 60,
			props: {text: 'Default Title', backgroundColor: '#0B1220', accentColor: '#2563EB'},
		},
	],
};

export const RemotionRoot: React.FC = () => {
	return (
		<Composition
			id="MainComposition"
			component={MainComposition}
			fps={FPS}
			width={WIDTH}
			height={HEIGHT}
			durationInFrames={defaultProps.scenes.reduce((sum, s) => sum + s.durationInFrames, 0)}
			schema={compositionPropsSchema}
			defaultProps={defaultProps}
			calculateMetadata={async ({props}) => ({
				durationInFrames: props.scenes.reduce((sum, s) => sum + s.durationInFrames, 0),
			})}
		/>
	);
};
