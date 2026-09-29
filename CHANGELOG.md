# Changelog

## 0.2.0a1

- Add adaptive default scoring for concentrated one-frame returns, alongside the original full-area mean. Keep the original route selectable with `--mode global` / `mode="global"`.
- Export an automatic source-pixel detail triple for salient-channel selections while retaining the context triple and original frame indices/times. Caller-selected regions still bound scoring and all crops.
- Emit `frameblink-review/2` with the winning channel, its raw score/threshold, ranking strength, both channels' diagnostics and optional detail coordinates/images.
- Add a reproducible 8×8-pixel pulse demo (`demo --small`) and controls for ordinary motion, fades, persistent changes and scope boundaries.
- Require constant decoded dimensions in both modes and reject non-integer Python `max_events` values so the output cap remains effective.
- Preserve the original T2 miss; document the new post-trial result and the continued limit under stronger simultaneous motion. Added candidate counts are not classified defect counts.

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
