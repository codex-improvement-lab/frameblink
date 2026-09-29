"""Author a tiny one-frame pulse; optional unrelated motion probes a limitation."""
from pathlib import Path
import argparse
import av
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def make_clip(output: Path, *, with_motion: bool = False):
    base = Image.new("RGB", (1280, 720), "#f8f5ef")
    draw = ImageDraw.Draw(base)
    font = lambda size: ImageFont.load_default(size=size)
    draw.rectangle((0, 0, 1279, 72), fill="#162439")
    draw.text((36, 24), "FRAMEBLINK / AUTHORED WORKSPACE", fill="white", font=font(24))
    draw.rounded_rectangle((28, 100, 260, 690), radius=16, fill="#e8edf2")
    for i, label in enumerate(["Overview", "Checks", "Changes", "Notes"]):
        draw.text((54, 140 + i * 60), label, fill="#56657a", font=font(22))
    draw.text((304, 108), "A small change in a large frame", fill="#162439", font=font(30))
    draw.text((304, 155), "Synthetic UI. One 8 x 8 pixel pulse. No customer recording.", fill="#56657a", font=font(19))
    draw.rounded_rectangle((300, 210, 1230, 480), radius=16, fill="white", outline="#d5dce5", width=2)
    draw.text((334, 238), "LOCAL REVIEW", fill="#56657a", font=font(18))
    for i, label in enumerate(["Source recording", "Adjacent frames", "Human inspection"]):
        y = 302 + i * 53
        draw.text((334, y), label, fill="#162439", font=font(23))
        draw.line((680, y + 14, 1060, y + 14), fill="#d5dce5", width=3)
    draw.text((304, 535), "The source stays on this device.", fill="#56657a", font=font(22))
    output.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(output), "w") as container:
        stream = container.add_stream("libx264", rate=30)
        stream.width, stream.height = base.size
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0", "preset": "ultrafast"}
        for index in range(90):
            image = base.copy()
            painter = ImageDraw.Draw(image)
            if index == 40:
                painter.rectangle((1120, 354, 1127, 361), fill="#162439")
            if with_motion:
                x = 310 + index * 8
                painter.rectangle((x, 600, x + 90, 650), fill="black")
            for packet in stream.encode(av.VideoFrame.from_image(image)):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "src/frameblink/assets/local-demo.mp4")
    parser.add_argument("--with-motion", action="store_true")
    args = parser.parse_args()
    make_clip(args.out, with_motion=args.with_motion)
