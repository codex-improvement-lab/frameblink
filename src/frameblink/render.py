"""Static, local-only human review of candidate adjacent frames."""

from __future__ import annotations

from html import escape

from PIL import Image, ImageDraw, ImageFont


INK = "#162439"
MUTED = "#56657a"
PAPER = "#f8f5ef"
WHITE = "#ffffff"
CORAL = "#e45f49"
LINE = "#d5dce5"


def _font(size: int):
    return ImageFont.load_default(size=size)


def _time(value: float | None) -> str:
    return f"{value:.3f}s" if value is not None else "time unavailable"


def make_triptych(before: Image.Image, center: Image.Image, after: Image.Image, event: dict, *, region=None) -> Image.Image:
    """Keep the three actual adjacent previews in one visibly labeled PNG."""
    frames = [before.convert("RGB"), center.convert("RGB"), after.convert("RGB")]
    frame_width, frame_height = frames[0].size
    if any(frame.size != (frame_width, frame_height) for frame in frames):
        raise ValueError("Candidate frames must have the same preview dimensions")
    panel_width, panel_height = max(360, frame_width), max(120, frame_height)
    margin, gap = 24, 16
    width = 2 * margin + 3 * panel_width + 2 * gap
    image_y = 156
    height = image_y + panel_height + 74
    card = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(card)
    scope = f"FRAMEBLINK / REGION {region[0]},{region[1]} / {region[2]}x{region[3]} SOURCE PIXELS" if region else "FRAMEBLINK / VISUAL REVERSION CANDIDATE"
    draw.text((margin, 18), scope, fill=MUTED, font=_font(18))
    draw.text((margin, 49), f"Candidate {event['rank']:02d}  /  center frame {event['centerFrameIndex']}", fill=INK, font=_font(27))
    draw.text((margin, 91), f"A-B-A score {event['score']:.3f}  |  Review the full video before deciding what happened.", fill=MUTED, font=_font(17))
    centers = [event["centerFrameIndex"] - 1, event["centerFrameIndex"], event["centerFrameIndex"] + 1]
    times = [event["beforeTimeSeconds"], event["centerTimeSeconds"], event["afterTimeSeconds"]]
    for index, (frame, number, time_value) in enumerate(zip(frames, centers, times)):
        x = margin + index * (panel_width + gap)
        label = ("BEFORE", "CANDIDATE", "AFTER")[index]
        color = CORAL if index == 1 else MUTED
        draw.rounded_rectangle((x - 1, image_y - 35, x + panel_width + 1, image_y + panel_height + 1), radius=7, fill=WHITE, outline=CORAL if index == 1 else LINE, width=2 if index == 1 else 1)
        draw.text((x + 10, image_y - 30), f"{label}  /  frame {number}  /  {_time(time_value)}", fill=color, font=_font(17))
        card.paste(frame, (x + (panel_width - frame_width) // 2, image_y + (panel_height - frame_height) // 2))
    footer = "Only this declared region is scored and shown. Review the full source; a candidate is not a bug verdict." if region else "A high score means the middle image differs while its neighbors are closer. It is not a bug verdict."
    draw.text((margin, image_y + panel_height + 28), footer, fill=MUTED, font=_font(17))
    return card


def render_html(result: dict) -> str:
    source = escape(result["source"]["basename"])
    region = result["analysis"].get("region")
    scope = f"Scoring region: x={region[0]}, y={region[1]}, width={region[2]}, height={region[3]} decoded source pixels. Triples show this crop; inspect the source video for surrounding context." if region else "Scoring area: the full decoded frame. Previews are resized for display."
    cards = []
    for event in result["events"]:
        center = event["centerFrameIndex"]
        path = escape(event["image"], quote=True)
        cards.append(
            f"<article><div class='eyebrow'>CANDIDATE {event['rank']:02d} · FRAME {center} · {_time(event['centerTimeSeconds'])}</div>"
            f"<h2>Momentary visual return, score {event['score']:.3f}</h2>"
            f"<p>The middle frame differs from both neighbors; its neighbors are more similar. Compare the three images, then check the source video.</p>"
            f"<img src='{path}' alt='Decoded source frames {center - 1}, {center}, and {center + 1}, arranged before, candidate, after.' loading='lazy'></article>"
        )
    if not cards:
        cards.append("<article><h2>No candidates above this threshold</h2><p>This is not proof that the recording has no bug. Smooth, persistent, or one-way changes need another method.</p></article>")
    limitations = "".join(f"<li>{escape(item)}</li>" for item in result["limitations"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frameblink review · {source}</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #f8f5ef; color: #162439; font: 16px/1.55 system-ui, sans-serif; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 48px 28px 72px; }}
.eyebrow {{ color: #56657a; font-size: 12px; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }}
h1 {{ font-size: clamp(34px, 5vw, 62px); line-height: 1.04; letter-spacing: -.04em; margin: 10px 0 18px; }}
h2 {{ font-size: 24px; line-height: 1.18; margin: 10px 0 8px; }}
p {{ max-width: 78ch; margin: 8px 0 18px; }}
.intro {{ color: #465871; font-size: 18px; }}
.stats {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 30px 0; }}
.stat {{ background: white; border: 1px solid #d5dce5; border-radius: 12px; padding: 12px 18px; min-width: 155px; }}
.stat strong {{ display: block; font-size: 27px; line-height: 1.1; }}
.stat span {{ color: #56657a; font-size: 13px; }}
article {{ margin: 28px 0; background: white; border: 1px solid #d5dce5; border-radius: 16px; padding: 22px; }}
article img {{ display: block; max-width: 100%; height: auto; margin-top: 18px; border-radius: 8px; }}
aside {{ margin-top: 42px; border-top: 1px solid #d5dce5; padding-top: 22px; color: #465871; }}
a {{ color: #254db3; }}
</style></head><body><main>
<div class="eyebrow">FRAMEBLINK / LOCAL VIDEO REVIEW</div>
<h1>Catch the frame that came back.</h1>
<p class="intro">Source: <strong>{source}</strong>. Frameblink ranks brief A→B→A visual changes for inspection. No source-code diagnosis or defect verdict is implied.</p>
<p>{scope}</p>
<div class="stats"><div class="stat"><strong>{result['framesDecoded']}</strong><span>decoded frames</span></div>
<div class="stat"><strong>{result['analysis']['candidateCount']}</strong><span>above threshold {result['analysis']['threshold']}</span></div>
<div class="stat"><strong>{result['analysis']['displayedCount']}</strong><span>adjacent triples shown</span></div></div>
{''.join(cards)}
<aside><h2>Read this with care</h2><ul>{limitations}</ul><p>Input SHA-256 and all scores are in <a href="events.json">events.json</a>. The hash identifies bytes, not authenticity. Review source frames and wording before sharing.</p></aside>
</main></body></html>
"""
