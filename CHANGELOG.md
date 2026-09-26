# Changelog

## 0.1.0a2

- Add optional `--region X,Y,W,H` and the Python `region=` argument to score small areas before downsampling and export matching cropped adjacent previews.
- Record region/image scope in JSON and visibly label regional PNG/HTML reports while preserving original frame indices, presentation times and the full source hash.
- Reject malformed/out-of-bounds regions before creating output, and reject changing decoded dimensions during a regional scan.
- Keep small preview labels readable and add authored local-region positive/negative controls plus clean-wheel regional first use.
- Document the bounded two-agent cursor trial: the original default scan produced no candidates; its later regional verification is a separate post-trial experiment, not a speedup or external adoption result.

## 0.1.0a1

- Added a local MP4/WebM CLI and Python API that rank short A→B→A visual return candidates without a model or system FFmpeg executable.
- Exported a static review HTML, capped adjacent-frame PNG triples and a source-bound `events.json` with scores, frame indices, available timestamps and limitations.
- Refused existing output directories, unsupported or oversized inputs, excessive duration/frame count and invalid parameters.
- Included reproducible authored positive and smooth-change control clips, local workflow tests, and a clean packaged first-use path.

Preview boundary: candidate ranking rather than automatic bug detection, root-cause analysis, privacy scrubbing, general video understanding, external adoption, or physical-device acceptance.
