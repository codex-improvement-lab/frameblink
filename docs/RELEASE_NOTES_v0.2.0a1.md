# Frameblink 0.2.0a1 preview

Small visual returns can now surface in the default scan without a preselected
region. An added salient-pixel comparison complements the original mean score;
selected small-change candidates get an automatic detail triple alongside the
context. Both use the actual adjacent decoded source frames.

Try `frameblink demo --small --out demo-review`. The authored 1280×720 video has
an 8×8 pulse at frame 40. Adaptive mode finds it; `--mode global` does not.
The original larger-jump `demo` and explicit `--region` paths remain available.

The output schema is now `frameblink-review/2`. Read [JSON_CONTRACT.md](JSON_CONTRACT.md)
before updating automated consumers. `--threshold` remains the full-area mean
cutoff; the supplemental channel has its own fixed cutoff recorded in JSON.

Validation records are in [evaluation.md](evaluation.md). The original ImGui T2
default miss is preserved. Its new four-candidate result is post-trial development
evidence. Two recordings downloaded after the candidate implementation was frozen
kept the same first selected frames under both modes; extra candidates were not
classified as additional defects.

A stronger unrelated animation can still hide a small return in the default
comparison. A caller-selected region recovered the authored concurrent-motion
case. Deliberate cursor movement and recording artifacts can also be candidates.
No absence-of-glitch, general time-saving, or external-adoption claim is made.

The package and public images contain authored media only. Public issue recordings
and their extracted pixels remain local research inputs.
