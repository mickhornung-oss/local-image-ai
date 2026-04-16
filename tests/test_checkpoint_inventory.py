from __future__ import annotations

import unittest
from pathlib import Path

import python.checkpoint_inventory as checkpoint_inventory


class CheckpointInventoryTests(unittest.TestCase):
    def test_is_sdxl_candidate_name(self) -> None:
        self.assertTrue(
            checkpoint_inventory.is_sdxl_candidate_name(
                "RealVisXL_V5.0_fp16.safetensors"
            )
        )
        self.assertFalse(
            checkpoint_inventory.is_sdxl_candidate_name("anything-v4.ckpt")
        )

    def test_find_checkpoint_by_name_is_case_insensitive(self) -> None:
        paths = [
            Path("RealVisXL_V5.0_fp16.safetensors"),
            Path("animagine-xl-4.0-opt.safetensors"),
        ]
        match = checkpoint_inventory.find_checkpoint_by_name(
            paths, "realvisxl_v5.0_fp16.safetensors"
        )
        self.assertEqual(match, Path("RealVisXL_V5.0_fp16.safetensors"))


if __name__ == "__main__":
    unittest.main()
