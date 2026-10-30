// Renders index.html to aggobai-dhaggobai.mp4 (1280x720, 30 fps) with song.mp3 as the soundtrack.
// Run from the repo root:  node tools/render-video.mjs
// Needs Playwright with Chromium, ffmpeg and python3 (for a throwaway local web server).
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';

const { chromium } = createRequire(import.meta.url)('playwright');
const FPS = 30, PORT = 8765, OUT = 'aggobai-dhaggobai.mp4';

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { stdio: 'ignore' });
await new Promise(r => setTimeout(r, 800));

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto(`http://127.0.0.1:${PORT}/index.html?capture`);
  await page.evaluate(() => document.fonts.ready);
  const dur = await page.evaluate(() => window.__DUR);

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-i', 'song.mp3',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '22', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const frames = Math.round(dur * FPS);
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.__render(t), f / FPS);
    const png = await page.locator('.stage').screenshot({ type: 'png' });
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 150 === 0) console.log(`frame ${f}/${frames}`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c ? rej(new Error(`ffmpeg exited ${c}`)) : res())));
  console.log('wrote', OUT);
} finally {
  await browser.close();
  server.kill();
}
