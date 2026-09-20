import {Img, Layout, Rect, Txt} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import {getContrastColor} from '../color';

export interface PosterProps {
	headline: string;
	ctaText: string;
	backgroundColor: string;
	accentColor: string;
	headlineColor?: string;
	ctaTextColor?: string;
	headlineFontFamily?: string;
	ctaFontFamily?: string;
	logoSrc?: string;
	decorationSrc?: string;
}

/**
 * Static - only frame 0 is ever captured (see render.mjs's poster path), so
 * no tweens here, unlike the video scenes. Reuses TitleReveal/Outro's visual
 * language (accent bar + headline, CTA badge) combined into one frame
 * instead of sequenced. Headline/CTA follow public/design/design.md's type
 * table: Crimson Pro for the headline, Inter 600 for the CTA button text -
 * pass headlineFontFamily/ctaFontFamily explicitly per brand; a future,
 * differently-branded job can leave them at the generic sans-serif default.
 */
export function* poster(view: Layout, props: PosterProps) {
	const {
		headline,
		ctaText,
		backgroundColor,
		accentColor,
		headlineColor,
		ctaTextColor,
		headlineFontFamily = 'sans-serif',
		ctaFontFamily = 'sans-serif',
		logoSrc,
		decorationSrc,
	} = props;
	const resolvedHeadlineColor = headlineColor ?? getContrastColor(backgroundColor);
	const resolvedCtaTextColor = ctaTextColor ?? getContrastColor(accentColor);

	view.add(
		<Rect
			size={['100%', '100%']}
			fill={backgroundColor}
			layout
			direction={'column'}
			alignItems={'center'}
			justifyContent={'center'}
			padding={108}
			gap={40}
		>
			{logoSrc && <Img src={logoSrc} width={140} />}
			<Rect width={96} height={10} fill={accentColor} />
			<Txt
				text={headline}
				fontFamily={headlineFontFamily}
				fontWeight={800}
				fontSize={84}
				lineHeight={'115%'}
				letterSpacing={-0.84}
				fill={resolvedHeadlineColor}
				textAlign={'center'}
				textWrap={true}
				width={860}
			/>
			<Rect fill={accentColor} radius={999} padding={[12, 24]}>
				<Txt
					text={ctaText}
					fontFamily={ctaFontFamily}
					fontWeight={600}
					fontSize={44}
					fill={resolvedCtaTextColor}
					textAlign={'center'}
				/>
			</Rect>
		</Rect>,
	);

	if (decorationSrc) {
		view.add(<Img src={decorationSrc} width={150} x={540 - 64 - 75} y={-960 + 64 + 75} />);
	}

	// A generator needs at least one yield to produce a frame.
	yield* waitFor(1 / 30);
}
