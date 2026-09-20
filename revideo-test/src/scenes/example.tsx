import {makeScene2D, Txt, Rect, Circle} from '@revideo/2d';
import {all, createRef, waitFor, easeOutCubic} from '@revideo/core';

export default makeScene2D('example', function* (view) {
  const title = createRef<Txt>();
  const subtitle = createRef<Txt>();
  const circle = createRef<Circle>();

  view.add(
    <Rect width={'100%'} height={'100%'} fill={'#1b1032'}>
      <Circle
        ref={circle}
        size={0}
        fill={'#ff7a45'}
        x={0}
        y={-620}
      />
      <Txt
        ref={title}
        text={'Revideo test render'}
        fontSize={96}
        fontFamily={'Arial'}
        fontWeight={800}
        fill={'#ffffff'}
        y={-40}
        opacity={0}
      />
      <Txt
        ref={subtitle}
        text={'Evaluating it as an alternative to Remotion'}
        fontSize={40}
        fontFamily={'Arial'}
        fill={'#c9b8ff'}
        y={60}
        opacity={0}
      />
    </Rect>,
  );

  yield* circle().size(2400, 1.2, easeOutCubic);
  yield* all(
    title().opacity(1, 0.6),
    title().y(-60, 0.6, easeOutCubic),
  );
  yield* waitFor(0.2);
  yield* subtitle().opacity(1, 0.6);
  yield* waitFor(1.5);
});
