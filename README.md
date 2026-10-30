# अग्गोबाई ढग्गोबाई — animated kids' music video

- `aggobai-dhaggobai.mp4` — the finished video (58 s, 1280×720, music + AI-sung vocals).
- `index.html` — the same video as an interactive web page with karaoke lyrics. Serve the folder (`python3 -m http.server`) and open it; press ▶.
- `song.js` — lyrics, word timing, melody and chords. Both the page and the voice tool read it.
- `vocals.mp3` — the sung vocal track.

## Rebuilding

1. Vocals (Meta MMS-TTS Marathi voice, re-pitched to the melody with the WORLD vocoder):
   `cd tools/voice && uv run python sing.py`
2. Video (needs Playwright + Chromium and ffmpeg):
   `node tools/render-video.mjs`

## Testing by hand

Open `index.html` through a local server, press ▶, and check that the singing, the
bouncing ball over the lyrics and each scene change line up with the beat.
