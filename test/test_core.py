from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import analyze_image  # noqa: E402


class CoreAnalysisTest(unittest.TestCase):
    def test_size_images_detect_beam_and_ball_centers(self) -> None:
        expected = {
            "15.bmp": (0.363, -0.363),
            "2.bmp": (0.242, 0.605),
            "5.bmp": (0.121, -0.363),
        }
        for image_name, (expected_dx, expected_dy) in expected.items():
            with self.subTest(image_name=image_name):
                analysis = analyze_image(ROOT / "sample" / "size" / image_name)
                result = analysis.result
                self.assertTrue(result.succeeded)
                self.assertAlmostEqual(result.dx_mm, expected_dx, places=3)
                self.assertAlmostEqual(result.dy_mm, expected_dy, places=3)


if __name__ == "__main__":
    unittest.main()
