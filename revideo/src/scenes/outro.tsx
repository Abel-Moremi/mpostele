import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {all, createEaseOutBack, createRef, waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

const easeOutBack = createEaseOutBack(1.7);

export interface OutroProps {
	text: string;
	backgroundColor: string;
	accentColor: string;
	textColor?: string;
	fontFamily?: string;
	logoSrc?: string;
	decorationSrc?: string;
}

export function* outro(view: Layout, props: OutroProps, durationInFrames: number, fps: number) {
	const {text, backgroundColor, accentColor, textColor, fontFamily = 'sans-serif', logoSrc, decorationSrc} = props;
	const resolvedTextColor = textColor ?? getContrastColor(accentColor);

	const root = createRef<Rect>();
	const logo = createRef<Img>();
	const badge = createRef<Rect>();
	const label = createRef<Txt>();
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
			gap={40}
		>
			{logoSrc && <Img ref={logo} src={logoSrc} width={96} opacity={0} />}
			<Rect ref={badge} fill={accentColor} radius={999} padding={[12, 24]} opacity={0} scale={1}>
				<Txt
					ref={label}
					text={text}
					fontFamily={fontFamily}
					fontWeight={600}
					fontSize={40}
					fill={resolvedTextColor}
					textAlign={'center'}
				/>
			</Rect>
		</Rect>,
	);

	if (decorationSrc) {
		view.add(
			<Img ref={decoration} src={decorationSrc} width={100} x={-540 + 48 + 50} y={960 - 48 - 50} opacity={0} />,
		);
	}

	yield* all(
		badge().opacity(1, 0.5),
		...(logoSrc ? [logo().opacity(1, 0.5)] : []),
		...(decorationSrc ? [decoration().opacity(1, 0.5)] : []),
	);
	yield* badge().scale(1.06, 0.3, easeOutBack).to(1, 0.3);

	const elapsedSeconds = 1.1;
	const totalSeconds = durationInFrames / fps;
	if (totalSeconds > elapsedSeconds) {
		yield* waitFor(totalSeconds - elapsedSeconds);
	}

	root().remove();
	decoration()?.remove();
}
