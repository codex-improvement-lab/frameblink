from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

import av
from PIL import Image, ImageDraw

from frameblink import FrameblinkError, scan_video
from frameblink.cli import main


ROOT = Path(__file__).resolve().parents[1]


class SalientTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".frameblink"
        scratch.mkdir(exist_ok=True)
        self.assertTrue(scratch.resolve().is_relative_to(ROOT.resolve()))
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to(scratch.resolve()))
        self.addCleanup(self.temporary.cleanup)

    def clip(self, name, paint, *, width=1280, height=720, frames=18):
        path = self.root / (name + ".mp4")
        with av.open(str(path), "w") as output:
            stream = output.add_stream("libx264", rate=30)
            stream.width, stream.height = width, height
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "18", "preset": "ultrafast"}
            for index in range(frames):
                image = Image.new("RGB", (width, height), "#20252b")
                paint(ImageDraw.Draw(image), index)
                for packet in stream.encode(av.VideoFrame.from_image(image)):
                    output.mux(packet)
            for packet in stream.encode():
                output.mux(packet)
        return path

    def test_default_discovers_a_tiny_return_and_clamps_detail_at_source_edge(self):
        def paint(draw, index):
            if index == 9:
                draw.rectangle((2, 2, 9, 9), fill="white")

        path = self.clip("corner", paint)
        legacy = scan_video(path, self.root / "global", mode="global")
        self.assertEqual(legacy["events"], [])
        result = scan_video(path, self.root / "adaptive")
        self.assertEqual([e["centerFrameIndex"] for e in result["events"]], [9])
        self.assertEqual(result["schemaVersion"], "frameblink-review/2")
        self.assertEqual(result["analysis"]["mode"], "adaptive")
        event = result["events"][0]
        self.assertEqual(event["scoreMethod"], "salient-pixels")
        self.assertEqual(event["detailRegion"][:2], [0, 0])
        self.assertEqual(event["detailRegion"][2:], [192, 144])
        self.assertAlmostEqual(event["centerTimeSeconds"], 9 / 30)
        self.assertTrue((self.root / "adaptive" / event["detailImage"]).is_file())
        self.assertEqual(result["source"]["sha256"], legacy["source"]["sha256"])

    def test_ordinary_translation_at_overlapping_and_disjoint_positions_is_not_a_return(self):
        for speed in (4, 32, 96):
            with self.subTest(speed=speed):
                def paint(draw, index):
                    x = 40 + index * speed
                    draw.rectangle((x, 250, x + 24, 290), fill="white")

                path = self.clip(f"motion-{speed}", paint, width=1920, frames=16)
                result = scan_video(path, self.root / f"motion-review-{speed}")
                self.assertEqual(result["events"], [])

    def test_static_persistent_and_fading_changes_are_not_returns(self):
        for kind in ("static", "persistent", "fade"):
            with self.subTest(kind=kind):
                def paint(draw, index):
                    if kind == "static" or (kind == "persistent" and index >= 9):
                        draw.rectangle((600, 300, 608, 308), fill="white")
                    elif kind == "fade":
                        level = 20 + index * 12
                        draw.rectangle((0, 0, 1279, 719), fill=(level, level, level))

                path = self.clip(kind, paint)
                result = scan_video(path, self.root / (kind + "-review"))
                self.assertEqual(result["events"], [])

    def test_explicit_region_excludes_a_detectable_return_outside_it(self):
        def paint(draw, index):
            if index == 9:
                draw.rectangle((1000, 400, 1008, 408), fill="white")

        path = self.clip("scoped", paint)
        result = scan_video(path, self.root / "scoped-review", region=(0, 0, 200, 200))
        self.assertEqual(result["events"], [])
        self.assertEqual(result["analysis"]["region"], [0, 0, 200, 200])

    def test_cli_global_mode_and_invalid_api_options(self):
        video = ROOT / "src/frameblink/assets/demo.mp4"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["scan", str(video), "--out", str(self.root / "cli"), "--mode", "global", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["mode"], "global")
        self.assertEqual(json.loads(stdout.getvalue())["firstCandidateFrame"], 40)
        for index, options in enumerate([{"mode": "other"}, {"max_events": 1.5}, {"max_events": True}]):
            output = self.root / f"invalid-{index}"
            with self.assertRaises(FrameblinkError):
                scan_video(video, output, **options)
            self.assertFalse(output.exists())
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["scan", str(video), "--out", str(self.root / "invalid-cli"), "--mode", "other"])


if __name__ == "__main__":
    unittest.main()
