# अग्गोबाई ढग्गोबाई — animated kids' music video

- `aggobai-dhaggobai.mp4` — the finished video (4:15, 1280×720) with `song.mp3` as its soundtrack.
- `index.html` — the same video as a web page with karaoke lyrics. Serve the folder (`python3 -m http.server`) and open it; press ▶. Click the progress bar to jump.
- `song.mp3` — the song recording.
- `song.js` — the timing: the song's beat, when each lyric line is sung, and which scene plays when.
  It was measured from `song.mp3` (beat tracking, plus speech recognition matched to the lyrics), so edit it by hand to fix any line that shows up early or late.

## Rebuilding the video

`node tools/render-video.mjs` (needs Playwright + Chromium and ffmpeg).

## Testing by hand

Open `index.html` through a local server, press ▶, and check that each lyric line appears while it is sung,
the bouncing ball moves along the words, and the scenes change with the song.
