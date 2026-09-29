# What the first preview has and has not shown

The original workflow pain is a coding agent receiving a short bug recording where a UI state is wrong for only one frame. Ordinary summaries may represent the before and after while omitting the middle. The useful output is a **small set of actual adjacent triples**, not a claim that a video is correct or incorrect.

The Lab first executed a public [FVP #68](https://github.com/wang-bin/fvp/issues/68) video with the same scene-change FFmpeg filter used by [video-debug](https://github.com/vladzima/video-debug) at source `465633fbb5768298f55d73a67c28a1be5377324e`. Twelve of 316 frames were kept, including a transient empty player region. That negative result stopped a generic “video scene extractor” idea. The Bash wrapper was not runnable in this Windows environment, so the executed result is the **equivalent filter**, not a full video-debug install trial. A separate [upstream issue](https://github.com/vladzima/video-debug/issues/1) reports the Windows Bash prerequisite.

The harder [Ghostty #11187](https://github.com/ghostty-org/ghostty/discussions/11187) recording has 258 frames. FFmpeg 6.1.1 selected **zero** frames at `scene > 0.03`. [Peepshow](https://github.com/t0mtaylor/peepshow) 0.9.2, run locally with telemetry/audio/report/index disabled, used its fallback and exported six evenly sampled frames. At a manually lowered scene threshold of `0.005`, it exported five deduplicated images; an individual relevant state can be recovered this way, but those images do not identify the preceding and following source frames as a triple. Its `--fps` route can export many more images. Frameblink's score placed zero-based frame 184 first, and frames 183/184/185 were visually inspected: the divider jumps for one frame and returns.

The score uses 202-pixel-wide grayscale frames and `min(MAD(A,B), MAD(B,C)) - MAD(A,C)`. The 0.1 threshold was chosen on Ghostty, **then frozen** before the separate [RustDesk #11192](https://github.com/rustdesk/rustdesk/issues/11192) Wayland/X11 trial. In PyAV 18.1.0 and NumPy 2.4.6, the Wayland recording gave 81 candidates in 1,355 decoded frames; the two highest ranked triples were visually inspected and showed a window appearing or disappearing in the middle frame. The reporter's X11 control recording gave zero candidates in 633 frames. The control is not a perfect matched experiment, and 81 candidates are not 81 independent bugs. The video was recorded with a phone, so camera and encoding artifacts may contribute. The public reporters' recordings and extracted frames are **not redistributed** in this repository or package.

[Framesleuth](https://github.com/thestackhub1/framesleuth-agent) is a broader local video-analysis stack. Its documented default Docker path downloads local vision/coding models; the Lab reviewed its public description but did not run it. A competent short Python+FFmpeg script also located the same A→B→A frames; the product increment is the reusable one-command decode, bounded ranking, source-bound JSON and human-readable adjacent export. The internal comparison below does not establish general time savings, external adoption or spontaneous tool discovery.

## Bounded agent pair: a small cursor transition

On 2026-09-26, two fresh-context agents received the same 9.85-second, 291-frame [public ImGui recording](https://github.com/ocornut/imgui/issues/7538). Both could use general video tools; one also received the released alpha.1 wheel and README and could choose whether to use it. Installation, instruction reading, failed attempts, image review and final reporting were inside the task boundary. Shared host/package caches and an already-downloaded input remained. This was an internal assigned-access pair, not an external user trial.

Both delivered visually reviewed adjacent cursor-shape transitions and declined to infer input latency or a cause. The general-tool arm completed in about 8m22s with 21 underlying tool calls; the tool-available arm completed in about 5m52s with 14. Orchestration wrappers are excluded consistently. The first task-relevant visual evidence appeared after about 224s and 180s respectively. These are descriptive observations from one pair, not a causal speedup estimate.

The consequential result was **zero default Frameblink candidates**. The tool-available agent's successful evidence came from a separate native-resolution regional script, not the product. Its README/installed libraries may have affected the fallback, and agent choices and report work differed; the elapsed-time gap cannot be assigned to Frameblink detection.

Alpha.2 subsequently added a caller-selected region. In a post-trial check using the region chosen during that investigation, it scored all 291 frames, found six above threshold, displayed five spaced candidates, and ranked the reviewed center frame 3 first; reviewed frame 16 was also present. This reused the investigated case and region, so it is feature verification rather than another blind result. The source pixels remain local and are not distributed here. Authored small-return and out-of-region controls exercise the implementation separately.

The repository's `demo.mp4` and `smooth.mp4` are authored. Unit/workflow tests establish the expected positive and negative behavior, input rejection, and escaped review text for these fixtures. Hosted CI and packaged install results are reported only after they actually pass. They cannot prove low false positives across arbitrary animations, variable camera footage, audio-bearing recordings or every platform codec.

## Adaptive 0.2 preview: a supplementary small-change comparison

The original 202-pixel mean-distance channel is retained. A supplemental view
caps the longest side at 960 pixels and compares the mean of the 64 strongest
absolute pixel differences, using a return-score cutoff of 8.0. These settings
were selected on previously inspected development inputs, then frozen before
the two additional source recordings below were downloaded.

The authored 1280×720, 8×8-pixel pulse is missed by the original mean channel and
selected at frame 40 by adaptive mode. Ordinary monotone fades, persistent
changes, stationary content and translating rectangles at overlapping/disjoint
positions produced no candidates in the scoped controls. A matching variant with
stronger simultaneous rectangle motion was missed by adaptive mode; a selected
region recovered the pulse. This limit remains part of the product description.

On the already investigated ImGui T2 input, adaptive mode found four candidates
without a supplied region: centers 59, 63, 3 and 281. Details for 59 and 3 were
visually inspected and show the cursor-shape return. This is development evidence,
not another blind trial; it does not replace the original zero-candidate result.

| Recording first executed after this implementation was frozen | Global mode | Adaptive mode | Reviewed result |
| --- | --- | --- | --- |
| [Zed #12827](https://github.com/zed-industries/zed/issues/12827), 976 frames | 40 candidates | 83 candidates | Both select frame 266 first; text is visibly restored in the center and fragmented in its neighbors |
| [Ghostty #1632](https://github.com/ghostty-org/ghostty/issues/1632), 1,499 frames | 40 candidates | 57 candidates | Both select frame 1252 first; the monitor region darkens in the center and returns in its neighbors |

The first six selections in both recordings were the same global-channel
selections. Increased candidate counts do not establish improved recall or a
false-positive rate. Only the first triples above were visually adjudicated;
the additional lower-ranked candidates were not classified. The phone recording
cannot distinguish application, display, camera or encoding causes.

Ghostty's original MOV was retained and remuxed to a video-only MP4 for the
supported input interface. Every decoded RGB frame and relative presentation
timestamp matched the original; no video re-encoding was performed. These videos
and all of their derived pixels remain outside the repository/package/social
assets. No external use or complete-task timing comparison was conducted here.
