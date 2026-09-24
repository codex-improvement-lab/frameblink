from hashlib import sha256
from pathlib import Path
import json
import tempfile
import unittest

from PIL import Image

from frameblink import FrameblinkError, scan_video


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "src/frameblink/assets/demo.mp4"
SMOOTH = ROOT / "tests/fixtures/smooth.mp4"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".frameblink"
        scratch.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_authored_one_frame_return_has_a_reviewable_triple(self):
        out = self.root / "candidate"
        result = scan_video(DEMO, out)
        self.assertEqual(result["framesDecoded"], 90)
        self.assertEqual(result["analysis"]["candidateCount"], 1)
        self.assertEqual(result["events"][0]["centerFrameIndex"], 40)
        self.assertEqual(result["source"]["sha256"], sha256(DEMO.read_bytes()).hexdigest())
        self.assertEqual(result["analysis"]["frameIndexBase"], 0)
        self.assertAlmostEqual(result["events"][0]["centerTimeSeconds"], 40 / 30, places=2)
        self.assertTrue((out / "review.html").is_file())
        self.assertTrue((out / "events.json").is_file())
        with Image.open(out / "candidate-01.png") as image:
            self.assertGreater(image.width, image.height * 2)
        self.assertEqual(json.loads((out / "events.json").read_text())["events"][0]["image"], "candidate-01.png")

    def test_smooth_change_is_not_a_momentary_return(self):
        out = self.root / "smooth"
        result = scan_video(SMOOTH, out)
        self.assertEqual(result["framesDecoded"], 60)
        self.assertEqual(result["analysis"]["candidateCount"], 0)
        self.assertEqual(result["events"], [])
        self.assertIn("not proof", (out / "review.html").read_text(encoding="utf-8"))
        self.assertEqual(list(out.glob("candidate-*.png")), [])

    def test_refuses_existing_output_and_bad_inputs_before_writing(self):
        existing = self.root / "existing"
        existing.mkdir()
        marker = existing / "keep.txt"
        marker.write_text("untouched", encoding="utf-8")
        with self.assertRaisesRegex(FrameblinkError, "already exists"):
            scan_video(DEMO, existing)
        self.assertEqual(marker.read_text(encoding="utf-8"), "untouched")
        bad_extension = self.root / "not-a-video.txt"
        bad_extension.write_text("hello", encoding="utf-8")
        with self.assertRaisesRegex(FrameblinkError, "MP4 and WebM"):
            scan_video(bad_extension, self.root / "not-created")
        self.assertFalse((self.root / "not-created").exists())
        corrupted = self.root / "corrupted.mp4"
        corrupted.write_bytes(b"not a video")
        with self.assertRaisesRegex(FrameblinkError, "Cannot open video"):
            scan_video(corrupted, self.root / "not-created-either")
        self.assertFalse((self.root / "not-created-either").exists())

    def test_escapes_user_video_name_in_review_html(self):
        renamed = self.root / "demo&note.mp4"
        renamed.write_bytes(DEMO.read_bytes())
        result = scan_video(renamed, self.root / "escaped")
        html = (self.root / "escaped/review.html").read_text(encoding="utf-8")
        self.assertIn("demo&amp;note.mp4", html)
        self.assertEqual(result["source"]["basename"], "demo&note.mp4")


if __name__ == "__main__":
    unittest.main()
