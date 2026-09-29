"""Decode every frame and rank short A-B-A visual returns for human review."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import math

import av
import numpy as np
from PIL import Image

from .render import make_triptych, render_html


MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 60.0
MAX_DECODED_FRAMES = 1800
MAX_DIMENSION = 4096
ANALYSIS_WIDTH = 202
SALIENT_LONGEST_SIDE = 960
SALIENT_PIXELS = 64
SALIENT_THRESHOLD = 8.0
DEFAULT_THRESHOLD = 0.1
DEFAULT_MAX_EVENTS = 6


class FrameblinkError(ValueError):
    """A bounded input or output setup error with a user-facing message."""


def _mean_absolute_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.abs(first.astype(np.int16) - second.astype(np.int16)).mean())


def _salient_difference(first: np.ndarray, second: np.ndarray) -> float:
    difference = np.subtract(first, second, dtype=np.int16)
    np.abs(difference, out=difference)
    values = difference.ravel()
    count = min(SALIENT_PIXELS, values.size)
    values.partition(values.size - count)
    return float(values[-count:].mean())


def _detail_region(before, center, after, area):
    """Locate one strong return for inspection; not a complete change mask."""
    ab = np.abs(np.subtract(before, center, dtype=np.int16))
    bc = np.abs(np.subtract(center, after, dtype=np.int16))
    ac = np.abs(np.subtract(before, after, dtype=np.int16))
    weights = np.maximum(np.minimum(ab, bc) - ac, 0)
    height, width = weights.shape
    block = 16
    padded = np.pad(weights, ((0, -height % block), (0, -width % block)))
    totals = padded.reshape(padded.shape[0] // block, block, padded.shape[1] // block, block).sum(axis=(1, 3))
    row, column = np.unravel_index(int(totals.argmax()), totals.shape)
    tile = weights[row * block:(row + 1) * block, column * block:(column + 1) * block]
    total = float(tile.sum())
    if total <= 0:
        return None
    ys, xs = np.indices(tile.shape)
    cx = column * block + float((tile * xs).sum()) / total + 0.5
    cy = row * block + float((tile * ys).sum()) / total + 0.5
    x, y, area_width, area_height = area
    crop_width, crop_height = min(192, area_width), min(144, area_height)
    if (crop_width, crop_height) == (area_width, area_height):
        return None
    left = min(max(round(cx * area_width / width) - crop_width // 2, 0), area_width - crop_width)
    top = min(max(round(cy * area_height / height) - crop_height // 2, 0), area_height - crop_height)
    return [x + left, y + top, crop_width, crop_height]


def _local_video(path: str | Path, output_dir: str | Path) -> tuple[Path, Path, int]:
    source = Path(path).expanduser()
    if not source.is_file():
        raise FrameblinkError(f"Video file does not exist: {source}")
    if source.suffix.lower() not in {".mp4", ".webm"}:
        raise FrameblinkError("Only local MP4 and WebM files are accepted in this preview")
    source = source.resolve()
    byte_count = source.stat().st_size
    if not 0 < byte_count <= MAX_SOURCE_BYTES:
        raise FrameblinkError(f"Video must be 1-{MAX_SOURCE_BYTES} bytes")
    output = Path(output_dir).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FrameblinkError(f"Output path already exists: {output}")
    if not output.parent.is_dir():
        raise FrameblinkError(f"Output parent directory does not exist: {output.parent}")
    return source, output, byte_count


def _time_relative(frame: av.VideoFrame, first_pts_time: float | None) -> tuple[float | None, float | None]:
    if frame.time is None:
        return None, first_pts_time
    current = float(frame.time)
    if not math.isfinite(current):
        return None, first_pts_time
    if first_pts_time is None:
        first_pts_time = current
    return max(0.0, current - first_pts_time), first_pts_time


def _region_tuple(region: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if region is None:
        return None
    if not isinstance(region, (tuple, list)) or len(region) != 4 or any(type(value) is not int for value in region):
        raise FrameblinkError("Region must contain four integers: x,y,width,height")
    x, y, width, height = region
    if x < 0 or y < 0 or width < 1 or height < 1:
        raise FrameblinkError("Region origin must be nonnegative and its width/height positive")
    return x, y, width, height


def _decode_and_score(source: Path, threshold: float, region: tuple[int, int, int, int] | None = None, mode: str = "adaptive") -> tuple[dict, list[dict]]:
    try:
        container = av.open(str(source))
    except av.FFmpegError as exc:
        raise FrameblinkError(f"Cannot open video: {exc}") from exc
    with container:
        streams = list(container.streams.video)
        if not streams:
            raise FrameblinkError("The file has no video stream")
        stream = streams[0]
        width = int(stream.codec_context.width)
        height = int(stream.codec_context.height)
        if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION:
            raise FrameblinkError(f"Video dimensions must be 1-{MAX_DIMENSION} pixels per side")
        metadata_seconds = float(container.duration / av.time_base) if container.duration is not None else None
        if metadata_seconds is not None and metadata_seconds > MAX_DURATION_SECONDS:
            raise FrameblinkError(f"Video metadata exceeds {MAX_DURATION_SECONDS:g} seconds")
        if region is not None and (region[0] + region[2] > width or region[1] + region[3] > height):
            raise FrameblinkError(f"Region must fit within the decoded {width}x{height} source")
        area_width, area_height = (region[2], region[3]) if region else (width, height)
        small_width = min(ANALYSIS_WIDTH, area_width)
        small_height = max(1, round(area_height * small_width / area_width))
        salient_scale = min(1.0, SALIENT_LONGEST_SIDE / max(area_width, area_height))
        salient_width = max(1, round(area_width * salient_scale))
        salient_height = max(1, round(area_height * salient_scale))
        scoring_area = region or (0, 0, width, height)
        before = center = None
        salient_before = salient_center = None
        salient_before_to_center = None
        before_to_center = None
        before_time = center_time = None
        first_pts_time = None
        last_time = None
        frame_count = 0
        candidates = []
        try:
            for frame_count, frame in enumerate(container.decode(stream), 1):
                if frame_count > MAX_DECODED_FRAMES:
                    raise FrameblinkError(f"Video exceeds {MAX_DECODED_FRAMES} decoded frames")
                current_time, first_pts_time = _time_relative(frame, first_pts_time)
                if current_time is not None:
                    last_time = current_time
                    if current_time > MAX_DURATION_SECONDS:
                        raise FrameblinkError(f"Decoded video exceeds {MAX_DURATION_SECONDS:g} seconds")
                if (frame.width, frame.height) != (width, height):
                    raise FrameblinkError("Scanning requires constant decoded frame dimensions")
                if region is None or region == (0, 0, width, height):
                    current = frame.to_ndarray(width=small_width, height=small_height, format="gray")
                    salient_current = frame.to_ndarray(width=salient_width, height=salient_height, format="gray") if mode == "adaptive" else None
                else:
                    x, y, area_width, area_height = region
                    crop = frame.to_ndarray(format="gray")[y:y + area_height, x:x + area_width]
                    current = np.asarray(Image.fromarray(crop).resize((small_width, small_height), Image.Resampling.BILINEAR))
                    salient_current = np.asarray(Image.fromarray(crop).resize((salient_width, salient_height), Image.Resampling.BILINEAR)) if mode == "adaptive" else None
                if before is not None and center is not None:
                    center_to_current = _mean_absolute_difference(center, current)
                    before_to_current = _mean_absolute_difference(before, current)
                    global_score = min(before_to_center, center_to_current) - before_to_current
                    salient_score = None
                    salient_distances = None
                    if mode == "adaptive":
                        salient_bc = _salient_difference(salient_center, salient_current)
                        salient_ac = _salient_difference(salient_before, salient_current)
                        salient_score = min(salient_before_to_center, salient_bc) - salient_ac
                        salient_distances = {
                            "beforeToCenter": round(salient_before_to_center, 6),
                            "centerToAfter": round(salient_bc, 6),
                            "beforeToAfter": round(salient_ac, 6),
                        }
                    channels = []
                    if global_score >= threshold:
                        channels.append((global_score / max(threshold, 1e-6), "global-mean", global_score, threshold))
                    if salient_score is not None and salient_score >= SALIENT_THRESHOLD:
                        channels.append((salient_score / SALIENT_THRESHOLD, "salient-pixels", salient_score, SALIENT_THRESHOLD))
                    if channels:
                        strength, method, score, applied_threshold = max(channels, key=lambda value: value[0])
                        event = {
                                "centerFrameIndex": frame_count - 2,
                                "beforeTimeSeconds": before_time,
                                "centerTimeSeconds": center_time,
                                "afterTimeSeconds": current_time,
                                "score": round(score, 6),
                                "scoreMethod": method,
                                "scoreThreshold": applied_threshold,
                                "rankStrength": round(strength, 6),
                                "globalScore": round(global_score, 6),
                                "beforeToCenterMad": round(before_to_center, 6),
                                "centerToAfterMad": round(center_to_current, 6),
                                "beforeToAfterMad": round(before_to_current, 6),
                                "salientScore": round(salient_score, 6) if salient_score is not None else None,
                                "salientDistances": salient_distances,
                            }
                        if method == "salient-pixels":
                            detail = _detail_region(salient_before, salient_center, salient_current, scoring_area)
                            if detail:
                                event["detailRegion"] = detail
                        candidates.append(event)
                    before_to_center = center_to_current
                    before, center = center, current
                    before_time, center_time = center_time, current_time
                    if mode == "adaptive":
                        salient_before_to_center = salient_bc
                        salient_before, salient_center = salient_center, salient_current
                elif center is None:
                    center, center_time = current, current_time
                    salient_center = salient_current
                else:
                    before, before_time = center, center_time
                    center, center_time = current, current_time
                    before_to_center = _mean_absolute_difference(before, center)
                    if mode == "adaptive":
                        salient_before, salient_center = salient_center, salient_current
                        salient_before_to_center = _salient_difference(salient_before, salient_center)
        except av.FFmpegError as exc:
            raise FrameblinkError(f"Could not decode video frames: {exc}") from exc

    if frame_count == 0:
        raise FrameblinkError("The video contains no decodable frames")
    info = {
        "framesDecoded": frame_count,
        "sourceDimensions": [width, height],
        "analysisDimensions": [small_width, small_height],
        "salientAnalysisDimensions": [salient_width, salient_height] if mode == "adaptive" else None,
        "durationMetadataSeconds": round(metadata_seconds, 6) if metadata_seconds is not None else None,
        "lastDecodedTimeSeconds": round(last_time, 6) if last_time is not None else None,
    }
    candidates.sort(key=lambda item: (-item["rankStrength"], item["centerFrameIndex"]))
    return info, candidates


def _source_digest(source: Path) -> str:
    digest = sha256()
    with source.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _select(candidates: list[dict], max_events: int) -> list[dict]:
    selected = []
    for event in candidates:
        center = event["centerFrameIndex"]
        if all(abs(center - prior["centerFrameIndex"]) >= 3 for prior in selected):
            selected.append(dict(event))
        if len(selected) == max_events:
            break
    return selected


def _images_for_events(source: Path, selected: list[dict], width: int, height: int, region: tuple[int, int, int, int] | None = None) -> tuple[dict, dict]:
    needed = {i + offset for item in selected for i in [item["centerFrameIndex"]] for offset in (-1, 0, 1)}
    if not needed:
        return {}, {}
    detail_regions = {event["centerFrameIndex"] + offset: event["detailRegion"] for event in selected if "detailRegion" in event for offset in (-1, 0, 1)}
    preview_width = min(560, width)
    preview_height = max(1, round(height * preview_width / width))
    if region:
        x, y, area_width, area_height = region
        scale = min(2.0, 560 / area_width, 420 / area_height)
        preview_width = max(1, round(area_width * scale))
        preview_height = max(1, round(area_height * scale))
    found = {}
    details = {}
    try:
        with av.open(str(source)) as container:
            stream = container.streams.video[0]
            for index, frame in enumerate(container.decode(stream)):
                if index in needed:
                    if region:
                        if (frame.width, frame.height) != (width, height):
                            raise FrameblinkError("Region scanning requires constant decoded frame dimensions")
                        crop = frame.to_image().crop((x, y, x + area_width, y + area_height))
                        method = Image.Resampling.NEAREST if scale >= 1 else Image.Resampling.LANCZOS
                        found[index] = crop.resize((preview_width, preview_height), method)
                    else:
                        found[index] = frame.to_image(width=preview_width, height=preview_height).copy()
                    if index in detail_regions:
                        dx, dy, dw, dh = detail_regions[index]
                        crop = frame.to_image().crop((dx, dy, dx + dw, dy + dh))
                        detail_scale = min(2.0, 560 / dw, 420 / dh)
                        details[index] = crop.resize((max(1, round(dw * detail_scale)), max(1, round(dh * detail_scale))), Image.Resampling.NEAREST)
                if len(found) == len(needed):
                    break
    except av.FFmpegError as exc:
        raise FrameblinkError(f"Could not extract candidate frames: {exc}") from exc
    if set(found) != needed:
        raise FrameblinkError("Could not recover every candidate's adjacent frames")
    return found, details


def scan_video(
    video_path: str | Path,
    output_dir: str | Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    max_events: int = DEFAULT_MAX_EVENTS,
    region: tuple[int, int, int, int] | None = None,
    mode: str = "adaptive",
) -> dict:
    """Scan one local video and write a candidate review to a new directory.

    A high score is a reason to inspect adjacent frames, not a bug verdict.
    ``region=(x, y, width, height)`` limits scoring and previews to decoded
    source pixels; frame indices and presentation times remain source-relative.
    """
    if mode not in ("adaptive", "global"):
        raise FrameblinkError("mode must be adaptive or global")
    if not math.isfinite(threshold) or not 0 <= threshold <= 255:
        raise FrameblinkError("Threshold must be a finite grayscale difference from 0 to 255")
    if type(max_events) is not int or not 1 <= max_events <= 12:
        raise FrameblinkError("max_events must be between 1 and 12")
    region = _region_tuple(region)
    source, output, byte_count = _local_video(video_path, output_dir)
    source_sha = _source_digest(source)
    info, candidates = _decode_and_score(source, threshold, region, mode)
    selected = _select(candidates, max_events)
    images, details = _images_for_events(source, selected, *info["sourceDimensions"], region)
    if source.stat().st_size != byte_count or _source_digest(source) != source_sha:
        raise FrameblinkError("Source video changed while scanning; retry with a stable file")
    for rank, event in enumerate(selected, 1):
        event["rank"] = rank
        event["image"] = f"candidate-{rank:02d}.png"
        if "detailRegion" in event:
            event["detailImage"] = f"candidate-{rank:02d}-detail.png"
    result = {
        "schemaVersion": "frameblink-review/2",
        "version": "0.2.0a1",
        "source": {"basename": source.name, "bytes": byte_count, "sha256": source_sha},
        **info,
        "analysis": {
            "method": "A-B-A candidate: min(d(before,center), d(center,after)) - d(before,after); full-area mean and optional salient-pixel mean absolute differences",
            "mode": mode,
            "ranking": "Eligible channel score divided by its threshold (floor 0.000001 for zero); not a probability or defect severity",
            "grayscaleWidth": ANALYSIS_WIDTH,
            "region": list(region) if region else None,
            "imageScope": "declared region crop" if region else "full frame preview",
            "threshold": threshold,
            "salient": {"enabled": mode == "adaptive", "longestSide": SALIENT_LONGEST_SIDE, "pixelCount": SALIENT_PIXELS, "threshold": SALIENT_THRESHOLD, "distance": "mean of the largest absolute grayscale pixel differences"},
            "candidateCount": len(candidates),
            "displayedCount": len(selected),
            "frameIndexBase": 0,
            "timestamps": "Decoder presentation times relative to the first timed frame; may differ from a player's seek display",
        },
        "events": selected,
        "limitations": [
            "Candidates are visual reversion signals, not software defect or root cause classifications.",
            "A missing candidate does not prove that the recording has no bug.",
            "A smooth change, long flicker, one-way flash, or large camera motion may need another method.",
            "Small returns can still be hidden by stronger simultaneous motion or downscaling. Try a caller-selected region when needed.",
            "Automatic detail rectangles are inspection aids, not exhaustive maps of every changing pixel.",
            "Images may contain private content; review every output before sharing.",
        ],
    }
    if region:
        result["limitations"].append("Only the caller-selected region was scored and shown; changes outside it are not evaluated. Cropped previews may be resized for display.")
    output.mkdir()
    for event in selected:
        center = event["centerFrameIndex"]
        image = make_triptych(images[center - 1], images[center], images[center + 1], event, region=region)
        image.save(output / event["image"], format="PNG", optimize=True)
        if "detailImage" in event:
            detail = make_triptych(details[center - 1], details[center], details[center + 1], event, region=event["detailRegion"], automatic_detail=True)
            detail.save(output / event["detailImage"], format="PNG", optimize=True)
    (output / "events.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "review.html").write_text(render_html(result), encoding="utf-8")
    return result
