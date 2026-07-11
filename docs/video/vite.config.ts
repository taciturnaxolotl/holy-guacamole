import {defineConfig} from 'vite';
import motionCanvasImport from '@motion-canvas/vite-plugin';

// @motion-canvas/vite-plugin ships CJS; normalize the default under ESM interop.
const motionCanvas =
  (motionCanvasImport as any).default ?? (motionCanvasImport as any);

export default defineConfig({
  plugins: [
    motionCanvas({
      project: './src/project.ts',
    }),
  ],
});
