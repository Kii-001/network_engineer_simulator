import unittest

from core.event_manager import EventManager
from core.save_manager import SaveManager


class TestSaveManager(unittest.TestCase):
    def setUp(self):
        self.save = SaveManager(":memory:")

    def test_defaults(self):
        self.assertTrue(self.save.get_bool("music"))
        self.assertFalse(self.save.get_bool("fullscreen"))

    def test_toggle_persists(self):
        self.assertFalse(self.save.toggle_bool("music"))
        self.assertFalse(self.save.get_bool("music"))

    def test_unknown_setting(self):
        with self.assertRaises(KeyError):
            self.save.set_setting("tidak_ada", "1")

    def test_player_name_validation(self):
        self.assertEqual(self.save.set_player_name("  Budi   Santoso "), "Budi Santoso")
        with self.assertRaises(ValueError):
            self.save.set_player_name("   ")

    def test_mission_result(self):
        self.save.add_mission_result(1, 3, 950, 42.5)
        self.assertEqual(self.save.get_mission_results()[0]["stars"], 3)
        with self.assertRaises(ValueError):
            self.save.add_mission_result(1, 5, 0, 0)


class TestEventManager(unittest.TestCase):
    def test_emit(self):
        got = []
        em = EventManager()
        em.subscribe("x", lambda v: got.append(v))
        self.assertEqual(em.emit("x", v=7), 1)
        self.assertEqual(got, [7])


if __name__ == "__main__":
    unittest.main()
