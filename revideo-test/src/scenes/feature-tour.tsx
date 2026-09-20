import {Circle, Layout, Polygon, Rect, Txt, makeScene2D} from '@revideo/2d';
import {
  all,
  createRef,
  createRefArray,
  easeInCubic,
  createEaseOutBack,
  easeInOutCubic,
  easeOutCubic,
  easeOutQuint,
  map,
  sequence,
  tween,
  waitFor,
} from '@revideo/core';

const BG = '#12102a';
const ORANGE = '#ff7a45';
const TEAL = '#22d3ee';
const PURPLE = '#a78bfa';
const INK = '#0d0b21';
const easeOutBack = createEaseOutBack(1.7);

interface Feature {
  color: string;
  sides: number;
  title: string;
  body: string;
}

const FEATURES: Feature[] = [
  {
    color: ORANGE,
    sides: 3,
    title: 'Generator scenes',
    body: 'yield* drives every tween on a timeline',
  },
  {
    color: TEAL,
    sides: 4,
    title: 'Flex layout',
    body: 'Rows, gaps and padding, not manual math',
  },
  {
    color: PURPLE,
    sides: 6,
    title: 'Server-side ffmpeg',
    body: 'Frames stream straight into a real encoder',
  },
];

interface Stat {
  color: string;
  value: number;
  suffix: string;
  label: string;
}

const STATS: Stat[] = [
  {color: ORANGE, value: 1920, suffix: 'px', label: 'render width'},
  {color: TEAL, value: 30, suffix: 'fps', label: 'frame rate'},
  {color: PURPLE, value: 124, suffix: '', label: 'frames captured'},
];

interface Bar {
  color: string;
  label: string;
  value: number;
}

const BARS: Bar[] = [
  {color: PURPLE, label: 'Wasm exporter', value: 0.15},
  {color: TEAL, label: 'Manual ffmpeg CLI', value: 0.62},
  {color: ORANGE, label: 'Server ffmpeg exporter', value: 0.9},
];

export default makeScene2D('feature-tour', function* (view) {
  view.fill(BG);

  const wipe = createRef<Circle>();
  const title = createRef<Txt>();
  const subtitle = createRef<Txt>();

  view.add(
    <>
      <Circle ref={wipe} size={0} fill={ORANGE} y={-620} />
      <Txt
        ref={title}
        text={'Revideo feature tour'}
        fontSize={92}
        fontFamily={'Arial'}
        fontWeight={800}
        fill={'#ffffff'}
        y={-40}
        opacity={0}
      />
      <Txt
        ref={subtitle}
        text={'A longer, multi-section render to stress-test the pipeline'}
        fontSize={36}
        fontFamily={'Arial'}
        fill={'#f4ece6'}
        y={50}
        opacity={0}
      />
    </>,
  );

  yield* wipe().size(2500, 1, easeOutCubic);
  yield* all(
    title().opacity(1, 0.5),
    title().y(-60, 0.5, easeOutCubic),
  );
  yield* waitFor(0.15);
  yield* subtitle().opacity(1, 0.5);
  yield* waitFor(1.1);

  yield* all(
    wipe().size(3400, 0.7, easeInCubic),
    wipe().fill(INK, 0.7),
    title().opacity(0, 0.4),
    subtitle().opacity(0, 0.4),
  );
  wipe().remove();
  view.fill(INK);
  title().remove();
  subtitle().remove();

  yield* featuresSection(view);
  yield* statsSection(view);
  yield* barsSection(view);
  yield* outroSection(view);
});

function* sectionHeading(view: Layout, text: string) {
  const heading = createRef<Txt>();
  view.add(
    <Txt
      ref={heading}
      text={text}
      fontSize={56}
      fontWeight={700}
      fontFamily={'Arial'}
      fill={'#ffffff'}
      y={-420}
      opacity={0}
    />,
  );
  yield* all(heading().opacity(1, 0.4), heading().y(-460, 0.4, easeOutCubic));
  return heading();
}

function* fadeOutAndRemove(...refs: {opacity: (v: number, d: number, e?: any) => any; remove: () => void}[]) {
  yield* all(...refs.map(r => r.opacity(0, 0.35, easeInCubic)));
  refs.forEach(r => r.remove());
}

function* featuresSection(view: Layout) {
  const heading = yield* sectionHeading(view, 'Built for code-driven video');

  const cards = createRefArray<Rect>();
  const row = createRef<Layout>();

  view.add(
    <Layout
      ref={row}
      layout
      direction={'row'}
      gap={60}
      justifyContent={'center'}
      alignItems={'start'}
      y={40}
    >
      {FEATURES.map(feature => (
        <Rect
          ref={cards}
          layout
          direction={'column'}
          alignItems={'center'}
          width={480}
          height={420}
          radius={28}
          fill={'#1d1a3c'}
          stroke={feature.color}
          lineWidth={3}
          padding={40}
          gap={24}
          opacity={0}
          y={80}
        >
          <Polygon sides={feature.sides} size={90} fill={feature.color} />
          <Txt
            text={feature.title}
            fontSize={38}
            fontWeight={700}
            fontFamily={'Arial'}
            fill={'#ffffff'}
            textAlign={'center'}
          />
          <Txt
            text={feature.body}
            fontSize={26}
            fontFamily={'Arial'}
            fill={'#c9c3e6'}
            textAlign={'center'}
            textWrap={true}
            width={380}
          />
        </Rect>
      ))}
    </Layout>,
  );

  yield* sequence(
    0.15,
    ...cards.map(card => all(card.opacity(1, 0.5, easeOutCubic), card.y(0, 0.5, easeOutBack))),
  );
  yield* waitFor(1.4);

  yield* fadeOutAndRemove(heading, row());
}

function* statsSection(view: Layout) {
  const heading = yield* sectionHeading(view, 'What this test render pushed through');

  const row = createRef<Layout>();
  const valueRefs = createRefArray<Txt>();

  view.add(
    <Layout ref={row} layout direction={'row'} gap={100} justifyContent={'center'} y={40}>
      {STATS.map(stat => (
        <Layout layout direction={'column'} alignItems={'center'} gap={16}>
          <Txt
            ref={valueRefs}
            text={'0'}
            fontSize={110}
            fontWeight={800}
            fontFamily={'Arial'}
            fill={stat.color}
          />
          <Txt
            text={stat.label}
            fontSize={30}
            fontFamily={'Arial'}
            fill={'#c9c3e6'}
          />
        </Layout>
      ))}
    </Layout>,
  );

  yield* sequence(
    0.2,
    ...valueRefs.map((ref, i) =>
      tween(1.1, v => {
        const value = Math.round(map(0, STATS[i].value, easeOutQuint(v)));
        ref.text(`${value}${STATS[i].suffix}`);
      }),
    ),
  );
  yield* waitFor(1.2);

  yield* fadeOutAndRemove(heading, row());
}

function* barsSection(view: Layout) {
  const heading = yield* sectionHeading(view, 'Relative time spent per export path');

  const chartArea = createRef<Layout>();
  const barRefs = createRefArray<Rect>();
  const maxHeight = 460;

  view.add(
    <Layout
      ref={chartArea}
      layout
      direction={'row'}
      alignItems={'end'}
      gap={90}
      height={maxHeight}
      y={60}
    >
      {BARS.map(bar => (
        <Layout layout direction={'column'} alignItems={'center'} gap={18}>
          <Rect ref={barRefs} width={190} height={0} radius={16} fill={bar.color} />
          <Txt
            text={bar.label}
            fontSize={26}
            fontFamily={'Arial'}
            fill={'#c9c3e6'}
            textAlign={'center'}
            width={220}
          />
        </Layout>
      ))}
    </Layout>,
  );

  yield* sequence(
    0.25,
    ...barRefs.map((bar, i) => bar.height(maxHeight * BARS[i].value, 0.8, easeOutBack)),
  );
  yield* waitFor(1.3);

  yield* fadeOutAndRemove(heading, chartArea());
}

function* outroSection(view: Layout) {
  const logo = createRef<Circle>();
  const text = createRef<Txt>();
  const fadeToBlack = createRef<Rect>();

  view.add(
    <>
      <Circle ref={logo} size={0} fill={ORANGE} />
      <Txt
        ref={text}
        text={'Rendered end-to-end with Revideo'}
        fontSize={44}
        fontWeight={700}
        fontFamily={'Arial'}
        fill={'#ffffff'}
        y={160}
        opacity={0}
      />
      <Rect ref={fadeToBlack} size={['100%', '100%']} fill={'#000000'} opacity={0} />
    </>,
  );

  yield* logo().size(220, 0.6, easeOutBack);
  yield* all(text().opacity(1, 0.4), text().y(120, 0.4, easeOutCubic));

  yield* logo().scale(1.15, 0.5).to(1, 0.5);
  yield* waitFor(0.4);

  yield* fadeToBlack().opacity(1, 0.8, easeInOutCubic);
}
