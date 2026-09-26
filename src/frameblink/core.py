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
DEFAULT_THRESHOLD = 0.1
DEFAULT_MAX_EVENTS = 6


class FrameblinkError(ValueError):
    """A bounded input or output setup error with a user-facing message."""


def _mean_absolute_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.abs(first.astype(np.int16) - second.astype(np.int16)).mean())


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


def _decode_and_score(source: Path, threshold: float, region: tuple[int, int, int, int] | None = None) -> tuple[dict, list[dict]]:
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
        before = center = None
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
                if region is not None and (frame.width, frame.height) != (width, height):
                    raise FrameblinkError("Region scanning requires constant decoded frame dimensions")
                if region is None or region == (0, 0, width, height):
                    current = frame.to_ndarray(width=small_width, height=small_height, format="gray")
                else:
                    x, y, area_width, area_height = region
                    crop = frame.to_ndarray(format="gray")[y:y + area_height, x:x + area_width]
                    current = np.asarray(Image.fromarray(crop).resize((small_width, small_height), Image.Resampling.BILINEAR))
                if before is not None and center is not None:
                    center_to_current = _mean_absolute_difference(center, current)
                    before_to_current = _mean_absolute_difference(before, current)
                    score = min(before_to_center, center_to_current) - before_to_current
                    if score >= threshold:
                        candidates.append(
                            {
                                "centerFrameIndex": frame_count - 2,
                                "beforeTimeSeconds": before_time,
                                "centerTimeSeconds": center_time,
                                "afterTimeSeconds": current_time,
                                "score": round(score, 6),
                                "beforeToCenterMad": round(before_to_center, 6),
                                "centerToAfterMad": round(center_to_current, 6),
                                "beforeToAfterMad": round(before_to_current, 6),
                            }
                        )
                    before_to_center = center_to_current
                    before, center = center, current
                    before_time, center_time = center_time, current_time
                elif center is None:
                    center, center_time = current, current_time
                else:
                    before, before_time = center, center_time
                    center, center_time = current, current_time
                    before_to_center = _mean_absolute_difference(before, center)
        except av.FFmpegError as exc:
            raise FrameblinkError(f"Could not decode video frames: {exc}") from exc

    if frame_count == 0:
        raise FrameblinkError("The video contains no decodable frames")
    info = {
        "framesDecoded": frame_count,
        "sourceDimensions": [width, height],
        "analysisDimensions": [small_width, small_height],
        "durationMetadataSeconds": round(metadata_seconds, 6) if metadata_seconds is not None else None,
        "lastDecodedTimeSeconds": round(last_time, 6) if last_time is not None else None,
    }
    candidates.sort(key=lambda item: (-item["score"], item["centerFrameIndex"]))
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


def _images_for_events(source: Path, selected: list[dict], width: int, height: int, region: tuple[int, int, int, int] | None = None) -> dict[int, object]:
    needed = {i + offset for item in selected for i in [item["centerFrameIndex"]] for offset in (-1, 0, 1)}
    if not needed:
        return {}
    preview_width = min(560, width)
    preview_height = max(1, round(height * preview_width / width))
    if region:
        x, y, area_width, area_height = region
        scale = min(2.0, 560 / area_width, 420 / area_height)
        preview_width = max(1, round(area_width * scale))
        preview_height = max(1, round(area_height * scale))
    found = {}
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
                if len(found) == len(needed):
                    break
    except av.FFmpegError as exc:
        raise FrameblinkError(f"Could not extract candidate frames: {exc}") from exc
    if set(found) != needed:
        raise FrameblinkError("Could not recover every candidate's adjacent frames")
    return found


def scan_video(
    video_path: str | Path,
    output_dir: str | Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    max_events: int = DEFAULT_MAX_EVENTS,
    region: tuple[int, int, int, int] | None = None,
) -> dict:
    """Scan one local video and write a candidate review to a new directory.

    A high score is a reason to inspect adjacent frames, not a bug verdict.
    ``region=(x, y, width, height)`` limits scoring and previews to decoded
    source pixels; frame indices and presentation times remain source-relative.
    """
    if not math.isfinite(threshold) or not 0 <= threshold <= 255:
        raise FrameblinkError("Threshold must be a finite grayscale difference from 0 to 255")
    if not 1 <= max_events <= 12:
        raise FrameblinkError("max_events must be between 1 and 12")
    region = _region_tuple(region)
    source, output, byte_count = _local_video(video_path, output_dir)
    source_sha = _source_digest(source)
    info, candidates = _decode_and_score(source, threshold, region)
    selected = _select(candidates, max_events)
    images = _images_for_events(source, selected, *info["sourceDimensions"], region)
    if source.stat().st_size != byte_count or _source_digest(source) != source_sha:
        raise FrameblinkError("Source video changed while scanning; retry with a stable file")
    for rank, event in enumerate(selected, 1):
        event["rank"] = rank
        event["image"] = f"candidate-{rank:02d}.png"
    result = {
        "schemaVersion": "frameblink-review/1",
        "version": "0.1.0a2",
        "source": {"basename": source.name, "bytes": byte_count, "sha256": source_sha},
        **info,
        "analysis": {
            "method": "A-B-A candidate: min(MAD(before,center), MAD(center,after)) - MAD(before,after)",
            "grayscaleWidth": ANALYSIS_WIDTH,
            "region": list(region) if region else None,
            "imageScope": "declared region crop" if region else "full frame preview",
            "threshold": threshold,
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
    (output / "events.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "review.html").write_text(render_html(result), encoding="utf-8")
    return result
