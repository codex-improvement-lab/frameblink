"""Render the repository's authored demo as a labelled 14-second walkthrough."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import av

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable with drawtext and libx264")
    parser.add_argument("--font", required=True, type=Path, help="Explicit local TTF/OTF font")
    parser.add_argument("--out", required=True, type=Path, help="Unused output directory")
    args = parser.parse_args()
    binary = shutil.which(args.ffmpeg)
    if not binary:
        parser.error("FFmpeg executable was not found")
    binary = str(Path(binary).resolve(strict=True))
    font = args.font.resolve(strict=True)
    output = args.out.resolve()
    if output.exists():
        parser.error("Output directory already exists")
    source = ROOT / "src/frameblink/assets/demo.mp4"
    report = ROOT / "docs/demo.png"
    cues = [
        ("Authored demo | 30 fps\nOriginal speed", 0, 3, "20"),
        ("0.1x slow motion\nSource frames 30-50 | change: frame 40", 3, 10, "20"),
        ("Before / center / after\nA candidate for human review", 10, 14, "20"),
        ("Frameblink | authored example, not a bug verdict", 0, 14, "h-text_h-20"),
    ]
    with tempfile.TemporaryDirectory(prefix="frameblink-walkthrough-") as directory:
        work = Path(directory).resolve()
        if work.parent != Path(tempfile.gettempdir()).resolve():
            raise RuntimeError("Unexpected temporary directory")
        for original, name in [(source, "source.mp4"), (report, "result.png"), (font, "font.ttf")]:
            shutil.copyfile(original, work / name)
        filters = [
            "[0:v]split=2[normalIn][slowIn]",
            "[normalIn]trim=start_frame=0:end_frame=90,setpts=PTS-STARTPTS,scale=1280:720,setsar=1[normal]",
            "[slowIn]trim=start_frame=30:end_frame=51,setpts=10*(PTS-STARTPTS),fps=30:round=down,tpad=stop_mode=clone:stop_duration=1,trim=end_frame=210,scale=1280:720,setsar=1[slow]",
            "[1:v]trim=end_frame=120,setpts=PTS-STARTPTS,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x111827,setsar=1[still]",
            "[normal][slow][still]concat=n=3:v=1:a=0[assembled]",
        ]
        captions = []
        for i, (text, start, end, y) in enumerate(cues):
            (work / f"caption-{i}.txt").write_text(text, encoding="utf-8")
            captions.append(
                f"drawtext=fontfile=font.ttf:textfile=caption-{i}.txt:fontsize=30:fontcolor=white:x=(w-text_w)/2:y={y}:enable='gte(t,{start})*lt(t,{end})':box=1:boxcolor=black@0.65:boxborderw=10"
            )
        filters.append("[assembled]" + ",".join(captions) + "[out]")
        command = [binary, "-hide_banner", "-n", "-i", "source.mp4", "-loop", "1", "-framerate", "30",
                   "-i", "result.png", "-filter_complex", ";".join(filters), "-map", "[out]", "-an", "-t", "14",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", "frameblink-explained.mp4"]
        subprocess.run(command, cwd=work, check=True, capture_output=True, timeout=90)
        video = work / "frameblink-explained.mp4"
        with av.open(str(video)) as container:
            stream = container.streams.video[0]
            frames = sum(1 for _ in container.decode(stream))
            if frames != 420 or stream.average_rate != 30 or (stream.width, stream.height) != (1280, 720):
                raise RuntimeError("Walkthrough does not match the 420-frame, 1280x720, 30fps plan")
        output.mkdir(parents=True)
        shutil.copyfile(video, output / video.name)
        record = {
            "authoredIllustration": True, "sourceSha256": digest(source), "reportSha256": digest(report),
            "fontSha256": digest(font), "outputSha256": digest(video), "frames": frames, "seconds": 14,
            "originalTransientFrame": 40, "slowOutputFrames": [190, 199], "resultStartsAtFrame": 300,
            "note": "This script illustrates the fixed repository demo, not arbitrary recordings or detection quality.",
        }
        (output / "render.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **record}))


if __name__ == "__main__":
    main()
