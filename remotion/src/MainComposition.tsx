import React from 'react';
import {Series} from 'remotion';
import type {CompositionProps, Scene} from './schema';
import {TitleReveal} from './scenes/TitleReveal';
import {CaptionOverlay} from './scenes/CaptionOverlay';
import {Outro} from './scenes/Outro';

/**
 * The only place a scene "component" name (agent-generated data) resolves
 * to an actual React component (hand-written code). This is what keeps
 * composition_agent.py's output data-only - it picks entries from this
 * fixed table, it never generates JSX.
 */
const renderScene = (scene: Scene) => {
	switch (scene.component) {
		case 'TitleReveal':
			return <TitleReveal {...scene.props} />;
		case 'CaptionOverlay':
			return <CaptionOverlay {...scene.props} durationInFrames={scene.durationInFrames} />;
		case 'Outro':
			return <Outro {...scene.props} />;
	}
};

export const MainComposition: React.FC<CompositionProps> = ({scenes}) => {
	return (
		<Series>
			{scenes.map((scene, i) => (
				<Series.Sequence key={i} durationInFrames={scene.durationInFrames}>
					{renderScene(scene)}
				</Series.Sequence>
			))}
		</Series>
	);
};
