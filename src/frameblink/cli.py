"""Small, explicit CLI for local adjacent-frame review."""

from __future__ import annotations

from argparse import ArgumentParser, ArgumentTypeError
from importlib.resources import as_file, files
from pathlib import Path
import json
import sys

from . import __version__
from .core import DEFAULT_MAX_EVENTS, DEFAULT_THRESHOLD, FrameblinkError, scan_video


def _region(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(part) for part in value.split(","))
    except ValueError as exc:
        raise ArgumentTypeError("region must be x,y,width,height in source pixels") from exc
    if len(parts) != 4:
        raise ArgumentTypeError("region must be x,y,width,height in source pixels")
    return parts


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(prog="frameblink", description="Find short A-B-A visual reversion candidates in a local screen recording.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="review one local MP4/WebM")
    scan.add_argument("video", type=Path)
    scan.add_argument("--out", type=Path, required=True, help="new output directory")
    scan.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="full-area mean threshold; the adaptive salient-pixel channel uses its own fixed cutoff")
    scan.add_argument("--mode", choices=["adaptive", "global"], default="adaptive", help="adaptive adds small-change scoring and automatic detail crops; global uses only the original full-area mean")
    scan.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    scan.add_argument("--region", type=_region, metavar="X,Y,W,H", help="score and show this source-pixel rectangle, with a top-left origin")
    scan.add_argument("--json", action="store_true", help="print a compact JSON summary")
    demo = commands.add_parser("demo", help="run the authored demonstration video")
    demo.add_argument("--out", type=Path, required=True, help="new output directory")
    demo.add_argument("--json", action="store_true", help="print a compact JSON summary")
    demo.add_argument("--region", type=_region, metavar="X,Y,W,H", help="score and show a rectangle in the authored demo")
    demo.add_argument("--mode", choices=["adaptive", "global"], default="adaptive")
    demo.add_argument("--small", action="store_true", help="use the authored tiny-pulse demo")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            asset = "assets/local-demo.mp4" if args.small else "assets/demo.mp4"
            with as_file(files("frameblink").joinpath(asset)) as video:
                result = scan_video(video, args.out, region=args.region, mode=args.mode)
        else:
            result = scan_video(args.video, args.out, threshold=args.threshold, max_events=args.max_events, region=args.region, mode=args.mode)
    except (FrameblinkError, OSError) as exc:
        print(f"frameblink: {exc}", file=sys.stderr)
        return 2
    summary = {
        "output": str(args.out.absolute()),
        "framesDecoded": result["framesDecoded"],
        "candidateCount": result["analysis"]["candidateCount"],
        "displayedCount": result["analysis"]["displayedCount"],
        "region": result["analysis"]["region"],
        "mode": result["analysis"]["mode"],
        "firstCandidateFrame": result["events"][0]["centerFrameIndex"] if result["events"] else None,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"Frameblink wrote {summary['displayedCount']} candidate triples from {summary['framesDecoded']} frames to {summary['output']}")
        print("Open review.html and inspect the source recording before claiming a bug.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
