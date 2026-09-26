from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

import av
from PIL import Image, ImageDraw

from frameblink import FrameblinkError, scan_video
from frameblink.cli import main


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "src/frameblink/assets/demo.mp4"


class RegionTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".frameblink"
        scratch.mkdir(exist_ok=True)
        assert scratch.resolve().is_relative_to(ROOT.resolve())
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temporary.name).resolve()
        assert self.root.is_relative_to(scratch.resolve())
        self.addCleanup(self.temporary.cleanup)

    def authored_clip(self):
        video = self.root / "small-return.mp4"
        with av.open(str(video), "w") as output:
            stream = output.add_stream("libx264", rate=30)
            stream.width, stream.height = 800, 400
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "0", "preset": "ultrafast"}
            for index in range(16):
                image = Image.new("RGB", (800, 400), "black")
                draw = ImageDraw.Draw(image)
                if index == 3:
                    draw.rectangle((40, 40, 340, 300), fill="white")
                if index == 8:
                    draw.rectangle((612, 152, 615, 155), fill="white")
                for packet in stream.encode(av.VideoFrame.from_image(image)):
                    output.mux(packet)
            for packet in stream.encode():
                output.mux(packet)
        return video

    def test_region_localizes_small_return_and_excludes_other_motion(self):
        video = self.authored_clip()
        whole = scan_video(video, self.root / "whole")
        regional = scan_video(video, self.root / "regional", region=(590, 130, 80, 80))
        self.assertEqual([event["centerFrameIndex"] for event in whole["events"]], [3])
        self.assertEqual([event["centerFrameIndex"] for event in regional["events"]], [8])
        self.assertEqual(regional["analysis"]["region"], [590, 130, 80, 80])
        self.assertEqual(regional["analysis"]["imageScope"], "declared region crop")
        self.assertEqual(regional["analysisDimensions"], [80, 80])
        self.assertEqual(regional["sourceDimensions"], [800, 400])
        self.assertAlmostEqual(regional["events"][0]["centerTimeSeconds"], 8 / 30)
        self.assertIn("Scoring region: x=590", (self.root / "regional/review.html").read_text(encoding="utf-8"))
        with Image.open(self.root / "regional/candidate-01.png") as image:
            self.assertGreaterEqual(image.width, 1100)  # Labels remain readable even for tiny crops.
        empty = scan_video(video, self.root / "empty-region", region=(700, 300, 80, 80))
        self.assertEqual(empty["events"], [])

    def test_rejects_malformed_or_out_of_source_regions_without_output(self):
        for index, region in enumerate([(0, 0, 20), (-1, 0, 20, 20), (0, 0, 0, 20), (0, 0, 20, -1), (0, 0, 20.5, 20), (False, 0, 20, 20), (630, 0, 20, 20), (0, 350, 20, 20)]):
            with self.subTest(region=region):
                out = self.root / f"invalid-{index}"
                with self.assertRaises(FrameblinkError):
                    scan_video(DEMO, out, region=region)
                self.assertFalse(out.exists())

    def test_explicit_whole_frame_region_preserves_scores(self):
        whole = scan_video(DEMO, self.root / "default")
        explicit = scan_video(DEMO, self.root / "explicit", region=(0, 0, 640, 360))
        self.assertEqual(whole["events"], explicit["events"])
        self.assertEqual(whole["analysisDimensions"], explicit["analysisDimensions"])

    def test_region_cli_rejects_incomplete_rectangle(self):
        out = self.root / "bad-cli"
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["scan", str(DEMO), "--out", str(out), "--region", "1,2,3"])
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
