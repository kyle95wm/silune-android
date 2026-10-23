#!/usr/bin/env python3
"""Exercise the daily sync's HEVC guard against patch regressions."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("hevc_guard", Path(__file__).with_name("check-hevc-override.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
ROOT = Path(__file__).resolve().parents[1]


class HevcGuardTest(unittest.TestCase):
    def test_current_patch_passes(self):
        self.assertEqual([], guard.check(ROOT))

    def test_removal_of_each_integration_fails(self):
        for relative in guard.REQUIRED:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for source in guard.REQUIRED:
                    target = root / source
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text((ROOT / source).read_text())
                (root / relative).unlink()
                self.assertTrue(guard.check(root))

    def test_changed_defaults_decode_policy_and_commented_out_patch_fail(self):
        mutations = [
            (guard.COMMON + "settings/PlayerSettingsStore.kt",
             "DEFAULT_IGNORE_HEVC_LEVEL_LIMITS = true", "DEFAULT_IGNORE_HEVC_LEVEL_LIMITS = false"),
            (guard.COMMON + "player/SiloPlayerFactory.kt",
             "infos.filter { it.hardwareAccelerated }.ifEmpty { infos }", "infos"),
            (guard.COMMON + "player/MediaCodecCapabilitiesProbe.kt",
             "capability.copy(levels = emptyList())", "capability"),
            (guard.COMMON + "settings/IgnoreHevcLevelLimitsBinder.kt",
             "MediaCodecCapabilitiesProbe.ignoreHevcLevelLimits = enabled",
             "// MediaCodecCapabilitiesProbe.ignoreHevcLevelLimits = enabled"),
        ]
        for relative, old, new in mutations:
            with self.subTest(change=old), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for source in guard.REQUIRED:
                    target = root / source
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text((ROOT / source).read_text())
                target = root / relative
                original = target.read_text()
                self.assertIn(old, original)
                target.write_text(original.replace(old, new))
                self.assertTrue(guard.check(root))


if __name__ == "__main__":
    unittest.main()
