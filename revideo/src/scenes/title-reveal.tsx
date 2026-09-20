import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

export interface TitleRevealProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	decorationSrc?: string;
}

export function* titleReveal(
	view: Layout,
	props: TitleRevealProps,
	durationInFrames: number,
	fps: number,
) {
	const {text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', decorationSrc} = props;
	const resolvedTextColor = textColor ?? getContrastColor(backgroundColor);

	const root = createRef<Rect>();
	const bar = createRef<Rect>();
	const headline = createRef<Txt>();
	const decoration = createRef<Img>();

	view.add(
		<Rect
			ref={root}
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			padding={108}
			gap={32}
		>
			<Rect ref={bar} width={64} height={8} fill={accentColor} opacity={0} />
			<Txt
				ref={headline}
				text={text}
				fontFamily={fontFamily}
				fontWeight={800}
				fontSize={72}
				lineHeight={'115%'}
				letterSpacing={-0.72}
				fill={resolvedTextColor}
				textAlign={'center'}
				textWrap={true}
				width={860}
				opacity={0}
				scale={0}
			/>
			{/* Corner decoration, positioned outside the centered stack - approximates
			the CSS top:48/right:48 inset from the Remotion version (exact corner
			anchoring isn't available the same way here, this is visually close). */}
		</Rect>,
	);

	if (decorationSrc) {
		view.add(
			<Img ref={decoration} src={decorationSrc} width={120} x={540 - 48 - 60} y={-960 + 48 + 60} opacity={0} />,
		);
	}

	yield* all(
		bar().opacity(1, 0.5),
		headline().opacity(1, 0.5),
		headline().scale(1, 0.6, easeOutBack),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);

	const elapsedSeconds = 0.6;
	const totalSeconds = durationInFrames / fps;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}

	root().remove();
	decoration()?.remove();
}
