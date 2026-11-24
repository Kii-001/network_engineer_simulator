import os
import unittest

import config
from tools.generate_assets import DEVICES, ICONS

DEVICE_TYPES = ["router", "switch", "managed_switch", "hub", "pc", "laptop", "server",
                "access_point", "firewall", "printer", "modem", "internet_cloud"]
SOUNDS = ["click", "hover", "place", "connect", "disconnect", "packet", "success", "failure",
          "error", "notification", "level_up", "typing"]


class TestAssetsExist(unittest.TestCase):
    def test_devices(self):
        self.assertEqual(sorted(DEVICES), sorted(DEVICE_TYPES))
        for d in DEVICE_TYPES:
            for suffix in ("", "_small"):
                self.assertTrue((config.ASSETS_DIR / "images" / "devices" / f"{d}{suffix}.png").exists(), d)

    def test_sounds_and_music(self):
        for s in SOUNDS:
            self.assertTrue((config.ASSETS_DIR / "sounds" / f"{s}.wav").exists(), s)
        self.assertTrue((config.ASSETS_DIR / "sounds" / "music" / "bgm_noc.wav").exists())

    def test_icons_and_ui(self):
        for name in ICONS:
            self.assertTrue((config.ASSETS_DIR / "images" / "icons" / f"{name}.png").exists(), name)
        for f in ("logo", "panel", "button_normal", "led_green", "cable_straight", "cable_fiber"):
            self.assertTrue((config.ASSETS_DIR / "images" / "ui" / f"{f}.png").exists(), f)


if __name__ == "__main__":
    unittest.main()
