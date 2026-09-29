# Frameblink review schema 2

Version 0.2 emits `schemaVersion: "frameblink-review/2"`. A successful CLI exit
includes an empty event list; it is not a statement that the recording is clean.

`source` still identifies the complete input bytes. `framesDecoded`,
`sourceDimensions`, frame indices and presentation times retain their meaning.
`analysisDimensions` describes the original mean channel. The optional
`salientAnalysisDimensions` describes the higher-resolution supplemental view.

`analysis.mode` is `adaptive` or `global`. `analysis.threshold` applies only to
the full-area mean channel; `analysis.salient` records its own enabled flag,
longest-side cap, pixel-count cap and threshold. The salient distance averages
the strongest `min(pixelCount, number of analyzed pixels)` absolute differences.

Each selected event contains:

- `scoreMethod`: `global-mean` or `salient-pixels`.
- `score` and `scoreThreshold`: the winning eligible channel's raw return score
  and cutoff, rather than always a full-area mean.
- `rankStrength`: score divided by its channel threshold, using a `0.000001`
  denominator for a configured zero threshold. This is a ranking quantity,
  not a probability, visual area, or defect severity.
- `globalScore`, `beforeToCenterMad`, `centerToAfterMad`, `beforeToAfterMad`:
  diagnostics from the original full-area mean channel, even when it did not win.
- `salientScore` and `salientDistances`: supplemental return score and its
  three pairwise distances; `null` in global mode.
- `image`: the context triple. `detailRegion: [x,y,width,height]` and
  `detailImage` are optional automatic inspection aids for salient selections.

All rectangles use decoded source pixels with a top-left origin. A detail stays
inside `analysis.region` when a caller supplies one. It highlights one strong
pointwise return and is not a complete change mask. Context remains available;
neither image is a defect classification. PNG previews can be resized.

At most `max_events` triples are selected with the existing three-frame spacing.
Each can add one detail triple, so up to twice that many PNG files may be written.
`candidateCount` counts qualifying frame centers, not bugs or independent events.

Schema 1 consumers must not compare every new `score` to `analysis.threshold`.
Use the event's `scoreMethod`/`scoreThreshold`, and treat added details as optional.
`--mode global` preserves the old scoring computation while still emitting schema 2.
