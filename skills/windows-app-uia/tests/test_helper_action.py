import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates"))
import helper_action as helper  # noqa: E402


class FakeWin32:
    def __init__(self):
        self.nodes = {1: ("Main", "myapp.exe", None, ""), 2: ("Other", "other.exe", None, ""),
                      10: ("", "", 1, "RICHEDIT50W"), 11: ("", "", 1, "Edit")}
        self.text = {10: "", 11: "hello"}
        self.keys = []

    def top_windows(self):
        return [h for h, n in self.nodes.items() if n[2] is None]

    def descendants(self, hwnd):
        return [h for h, n in self.nodes.items() if n[2] == hwnd]

    def class_name(self, hwnd):
        return self.nodes[hwnd][3]

    def title(self, hwnd):
        return self.nodes[hwnd][0]

    def process_name(self, hwnd):
        return self.nodes[hwnd][1]

    def control_text(self, hwnd):
        return self.text[hwnd]

    def set_text(self, hwnd, text):
        self.text[hwnd] = text

    def post_key(self, hwnd, key):
        self.keys.append((hwnd, key))


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.win = FakeWin32()

    def test_lists_only_target_process_windows(self):
        self.assertEqual(helper.run({"action": "windows"}, self.win)["items"], [{"windowTitle": "Main"}])

    def test_submit_sets_text_and_presses_enter_once(self):
        result = helper.run({"action": "submit", "windowTitle": "Main", "text": "a\nb"}, self.win)
        self.assertEqual(result["status"], "dispatched")
        self.assertEqual(self.win.text[10], "a\r\nb")
        self.assertEqual(self.win.keys, [(10, helper.VK_RETURN)])

    def test_existing_draft_and_duplicates_stop_before_dispatch(self):
        self.win.text[10] = "draft"
        self.assertEqual(helper.run({"action": "submit", "windowTitle": "Main", "text": "x"}, self.win)["reason"],
                         "existing_draft_preserved")
        self.win.nodes[3] = ("Main", "myapp.exe", None, "")
        self.assertEqual(helper.run({"action": "read_text", "windowTitle": "Main"}, self.win)["reason"],
                         "duplicate_window_title")
        self.assertEqual(self.win.keys, [])


if __name__ == "__main__":
    unittest.main()
