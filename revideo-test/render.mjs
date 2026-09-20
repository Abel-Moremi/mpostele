import {renderVideo} from '@revideo/renderer';

const file = await renderVideo({
  projectFile: './src/project.ts',
  settings: {
    outFile: 'feature-tour.mp4',
    outDir: './output',
    logProgress: true,
  },
});

console.log('Rendered to', file);
