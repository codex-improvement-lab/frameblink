# Watch the authored example

[Download or play the 14-second MP4](https://github.com/codex-improvement-lab/frameblink/releases/download/v0.1.0a2/frameblink-explained.mp4).

The walkthrough shows the repository's authored UI clip at its original 30 fps for three seconds, then source frames 30–50 at explicitly labelled 0.1× speed, then the existing before/center/after result image for four seconds. The sidebar changes at source frame 40 (1.333 seconds). In the slow section it occupies output frames 190–199, starting at 6.333 seconds. The result image begins at output frame 300 (10 seconds).

The final output is 1280×720, 30 fps and 420 frames. The source already has no audio; no speech or audio-alignment claim is made. Captions say that this is authored footage and a visual candidate requiring review. Slow motion does not describe the original event's duration.

This is an explanation of the product's narrow output, not another evaluation case or independent adoption result. No public issue recording is included.

## Reproduce from this source checkout

The normal `frameblink demo` command does not need a separate FFmpeg installation. Rebuilding this optional promotional walkthrough does require FFmpeg with `drawtext`/`libx264` and an explicitly supplied licensed font:

```sh
python scripts/make_walkthrough.py --ffmpeg /path/to/ffmpeg --font /path/to/Inter.ttf --out ./walkthrough
```

The script uses only the repository's authored `src/frameblink/assets/demo.mp4`, `docs/demo.png` and the supplied font. It refuses an existing output directory and writes an MP4 plus hashes in `render.json`. It is not a general-purpose video editor. The supplied font is not included in the outputs.

The published example used FFmpeg 6.1.1 and Inter from [Google Fonts](https://github.com/google/fonts/blob/23e54b51ddffbc7713c583748e3bd86f62b1fa4a5606bad55/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf), SHA-256 `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031`, under the [SIL Open Font License](https://github.com/google/fonts/blob/23e54b51ddffbc7713c583748e3bd86f62b1fa4a5606bad55/ofl/inter/OFL.txt). Other renderer/font versions can change pixels; inspect the result before sharing.
