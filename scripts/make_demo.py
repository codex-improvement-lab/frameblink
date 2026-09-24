"""Build two authored local UI clips; no public issue footage is included."""

from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def _font(size: int):
    return ImageFont.load_default(size=size)


def _frame(sidebar_width: int) -> Image.Image:
    canvas = Image.new("RGB", (640, 360), "#f5f7fb")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 640, 52), fill="#1a2942")
    draw.text((22, 16), "FIELD NOTES", fill="white", font=_font(20))
    draw.rectangle((0, 52, sidebar_width, 360), fill="#e4ebf4")
    draw.text((24, 76), "Tasks", fill="#31435e", font=_font(21))
    draw.rounded_rectangle((16, 116, sidebar_width - 16, 157), radius=8, fill="#d0deef")
    draw.text((26, 127), "Review", fill="#17345d", font=_font(18))
    draw.text((25, 178), "Sources", fill="#536880", font=_font(17))
    draw.text((25, 215), "Exports", fill="#536880", font=_font(17))
    draw.rectangle((sidebar_width, 52, sidebar_width + 2, 360), fill="#788ca6")
    x = sidebar_width + 28
    draw.text((x, 77), "A task with a clear result", fill="#23364f", font=_font(24))
    draw.rounded_rectangle((x, 124, 606, 280), radius=13, fill="white", outline="#cbd6e6", width=2)
    draw.text((x + 18, 145), "Source review", fill="#213955", font=_font(20))
    draw.text((x + 18, 189), "The sidebar should stay still.", fill="#536880", font=_font(17))
    draw.rounded_rectangle((x + 18, 229, min(590, x + 145), 262), radius=7, fill="#3468b6")
    draw.text((x + 30, 235), "Open", fill="white", font=_font(16))
    return canvas


def _encode(path: Path, widths: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as output:
        stream = output.add_stream("libx264", rate=30)
        stream.width, stream.height = 640, 360
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "18", "preset": "ultrafast"}
        for width in widths:
            frame = av.VideoFrame.from_image(_frame(width))
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


if __name__ == "__main__":
    single_frame = [178] * 90
    single_frame[40] = 306
    _encode(ROOT / "src/frameblink/assets/demo.mp4", single_frame)
    smooth = [178 + round(i * 118 / 59) for i in range(60)]
    _encode(ROOT / "tests/fixtures/smooth.mp4", smooth)
    print("Built authored A-B-A demo and smooth-change control")
