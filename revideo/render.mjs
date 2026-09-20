/**
 * CLI entrypoint used by app/media/revideo_cli.py in place of Remotion's
 * `npx remotion render/still <id> <out> --props <file>`. Usage:
 *
 *   node render.mjs --project video|poster --props <props.json> --out <out-path>
 *
 * `video` renders src/video-project.ts (the composition_spec's scene list)
 * straight to the requested .mp4. `poster` has no Revideo equivalent for a
 * single-frame "still" render (renderVideo()/renderPartialVideo() explicitly
 * reject the image-sequence exporter - "Please use the editor to export
 * images", confirmed by reading @revideo/renderer's source) - so it renders
 * a near-zero-duration clip through the same FFmpeg-exporter path, then
 * extracts frame 0 as a PNG and discards the intermediate video.
 */
// Revideo phones a render-started/error event home to PostHog by default -
// keep this render path as local-only as the Remotion one was ("Nothing
// leaves the machine", docs-mpostele/03 Workflow/03 Video Rendering Path.md).
process.env.DISABLE_TELEMETRY = 'true';

import {execFileSync} from 'node:child_process';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';

import {renderVideo} from '@revideo/renderer';
import ffmpegInstaller from '@ffmpeg-installer/ffmpeg';

import {compositionPropsSchema, posterPropsSchema} from './schema.mjs';

function parseArgs(argv) {
	const args = {};
	for (let i = 0; i < argv.length; i += 2) {
		const key = argv[i].replace(/^--/, '');
		args[key] = argv[i + 1];
	}
	if (!args.project || !args.props || !args.out) {
		throw new Error('Usage: node render.mjs --project video|poster --props <props.json> --out <out-path>');
	}
	if (args.project !== 'video' && args.project !== 'poster') {
		throw new Error(`--project must be "video" or "poster", got ${JSON.stringify(args.project)}`);
	}
	return args;
}

async function readProps(propsPath, project) {
	const fs = await import('node:fs/promises');
	const raw = JSON.parse(await fs.readFile(propsPath, 'utf-8'));
	if (project === 'video') {
		return compositionPropsSchema.parse(raw);
	}
	return posterPropsSchema.parse(raw);
}

async function renderVideoProject(props, outPath) {
	const outDir = path.dirname(outPath);
	const outFile = path.basename(outPath);
	await renderVideo({
		projectFile: './src/video-project.ts',
		variables: props,
		settings: {outFile, outDir, logProgress: true},
	});
}

async function renderPosterProject(props, outPath) {
	const tmpDir = mkdtempSync(path.join(tmpdir(), 'revideo-poster-'));
	const tmpVideo = 'poster.mp4';
	await renderVideo({
		projectFile: './src/poster-project.ts',
		variables: {props},
		settings: {outFile: tmpVideo, outDir: tmpDir, logProgress: true},
	});

	// Extract straight to outPath rather than a tmp path + rename - the
	// caller's output directory always already exists by the time this
	// runs (video_engine.py/poster_engine.py both mkdir it before calling
	// run_revideo), and this sidesteps renameSync's EXDEV failure when the
	// OS temp dir and the output dir are on different volumes/mounts.
	execFileSync(ffmpegInstaller.path, ['-y', '-i', path.join(tmpDir, tmpVideo), '-frames:v', '1', outPath]);
	rmSync(tmpDir, {recursive: true, force: true});
}

async function main() {
	const args = parseArgs(process.argv.slice(2));
	const props = await readProps(args.props, args.project);

	if (args.project === 'video') {
		await renderVideoProject(props, args.out);
	} else {
		await renderPosterProject(props, args.out);
	}
	console.log('Rendered to', args.out);
}

main().catch(err => {
	console.error(err);
	process.exit(1);
});
