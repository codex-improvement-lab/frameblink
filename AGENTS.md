# Frameblink

Frameblink's narrow promise is to rank short-lived A-B-A visual reversion
candidates in an already captured local MP4/WebM and export adjacent before,
center and after frames for human review. It does not classify bugs, infer root
causes, inspect source code, verify user claims, or prove the absence of a glitch.

Caller-selected regions use decoded source-pixel x/y/width/height coordinates.
Score and preview only that rectangle, record the scope in JSON and images,
and preserve original frame indices/times. Never describe a region scan as
coverage of the rest of the frame.

Keep one complete local CLI/API loop with strict file, duration, resolution and
frame-count limits. Never upload source video, call a model, sign in, post, or
send telemetry. Refuse existing output directories and label the output as
candidate evidence requiring human review. Source videos and output images may
contain private content; preview before sharing.

The public demo must be authored and reproducible. Public issue recordings used
in the Lab's research are not package assets, social images, or redistributed
test fixtures. Separate synthetic tests, automated CI, local visual review,
physical-device use and external adoption claims.

This first-level directory is an independent Git repository. Follow the parent
workspace guide, run Git/tests/package/release commands here, preserve sibling
projects and other people's edits, and never combine repository histories.
