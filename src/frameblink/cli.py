"""Small, explicit CLI for local adjacent-frame review."""

from __future__ import annotations

from argparse import ArgumentParser
from importlib.resources import as_file, files
from pathlib import Path
import json
import sys

from . import __version__
from .core import DEFAULT_MAX_EVENTS, DEFAULT_THRESHOLD, FrameblinkError, scan_video


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(prog="frameblink", description="Find short A-B-A visual reversion candidates in a local screen recording.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="review one local MP4/WebM")
    scan.add_argument("video", type=Path)
    scan.add_argument("--out", type=Path, required=True, help="new output directory")
    scan.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    scan.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS)
    scan.add_argument("--json", action="store_true", help="print a compact JSON summary")
    demo = commands.add_parser("demo", help="run the authored demonstration video")
    demo.add_argument("--out", type=Path, required=True, help="new output directory")
    demo.add_argument("--json", action="store_true", help="print a compact JSON summary")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            with as_file(files("frameblink").joinpath("assets/demo.mp4")) as video:
                result = scan_video(video, args.out)
        else:
            result = scan_video(args.video, args.out, threshold=args.threshold, max_events=args.max_events)
    except (FrameblinkError, OSError) as exc:
        print(f"frameblink: {exc}", file=sys.stderr)
        return 2
    summary = {
        "output": str(args.out.absolute()),
        "framesDecoded": result["framesDecoded"],
        "candidateCount": result["analysis"]["candidateCount"],
        "displayedCount": result["analysis"]["displayedCount"],
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
