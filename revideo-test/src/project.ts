import {makeProject} from '@revideo/core';

import featureTour from './scenes/feature-tour?scene';

export default makeProject({
  scenes: [featureTour],
  variables: {},
  settings: {
    rendering: {
      exporter: {
        name: '@revideo/core/ffmpeg',
        options: {format: 'mp4'},
      },
    },
  },
});
