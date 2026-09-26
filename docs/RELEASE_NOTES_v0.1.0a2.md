# Frameblink 0.1.0a2 — inspect a declared region

Small cursor or text changes can vanish when the whole recording is reduced for scoring. Alpha.2 adds `--region X,Y,W,H` (Python: `region=(x,y,width,height)`) so an agent can focus on a known source-pixel area and immediately review its adjacent crops.

```sh
frameblink demo --out ./region-demo --region 160,60,200,240
```

The mode keeps the original frame numbers, decoder times and whole-file hash. JSON, PNG and HTML identify the selected rectangle. Invalid rectangles fail before output is created. Crops may be resized for readability; nothing outside the rectangle is evaluated. Default whole-frame scoring remains available.

The motivation came from a bounded internal pair using a public ImGui recording. Both agents produced valid cursor-change examples, but alpha.1's default scan returned no candidates and the tool-enabled agent used a separate regional script. A subsequent region-mode run localized reviewed examples. That is post-trial feature verification; it is not a second blind trial, a demonstrated general speedup or external adoption.

The included demo, its regional illustration and the tiny-return test clips are authored. No public issue footage or extracted pixels are included in this release. Tests cover a small in-region return, unrelated out-of-region motion, an empty region, invalid rectangles, the existing workflow and clean packaged first use. Physical-device validation and broad codec/false-positive claims remain outside this preview.
