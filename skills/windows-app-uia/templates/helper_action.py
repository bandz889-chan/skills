#!/usr/bin/env python3
"""Template: one Windows helper call = one user action. stdin JSON -> stdout JSON.

Replace PROCESS / classes with what uia_dump.py showed for your app. Actions:

    {"action": "windows"}                                         # list target windows, read-only
    {"action": "read_text", "windowTitle": "Exact title"}         # WM_GETTEXT of the one text control
    {"action": "submit", "windowTitle": "Exact title", "text": "…"}  # empty composer -> set text -> Enter

Irreversible actions (submit) must go through operation_journal.py in the caller,
so a lost response is never retried under a new ID.
"""

import json
import sys
import time
from pathlib import Path

PROCESS = "myapp.exe"          # TODO: executable name (lower case)
COMPOSER_CLASS = "RICHEDIT50W"  # TODO: input control class from the win32 dump
TEXT_CLASS = "Edit"             # TODO: read-only text control class, if any
WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x000C, 0x000D, 0x000E
WM_KEYDOWN, WM_KEYUP, VK_RETURN = 0x0100, 0x0101, 0x0D


class Win32:
    """Minimal ctypes layer; swap for a fake in tests."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        self.c, self.w = ctypes, w
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        L, W = ctypes.c_ssize_t, ctypes.c_size_t
        self.PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, L)
        self.u.EnumWindows.argtypes = [self.PROC, L]
        self.u.EnumChildWindows.argtypes = [w.HWND, self.PROC, L]
        self.u.SendMessageW.argtypes, self.u.SendMessageW.restype = [w.HWND, w.UINT, W, L], L
        self.u.PostMessageW.argtypes = [w.HWND, w.UINT, W, L]
        self.u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.k.OpenProcess.restype = w.HANDLE
        self.k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
        for name, args in (("GetClassNameW", [w.HWND, w.LPWSTR, ctypes.c_int]), ("GetWindowTextW", [w.HWND, w.LPWSTR, ctypes.c_int]),
                           ("IsWindowVisible", [w.HWND]), ("MapVirtualKeyW", [w.UINT, w.UINT])):
            getattr(self.u, name).argtypes = args
        self.k.CloseHandle.argtypes = [w.HANDLE]

    def _enum(self, parent=None):
        found = []
        callback = self.PROC(lambda hwnd, _: found.append(hwnd) or True)
        (self.u.EnumWindows(callback, 0) if parent is None else self.u.EnumChildWindows(parent, callback, 0))
        return found

    def top_windows(self):
        return [h for h in self._enum() if self.u.IsWindowVisible(h)]

    def descendants(self, hwnd):
        return self._enum(hwnd)

    def class_name(self, hwnd):
        buffer = self.c.create_unicode_buffer(256)
        self.u.GetClassNameW(hwnd, buffer, 256)
        return buffer.value

    def title(self, hwnd):
        buffer = self.c.create_unicode_buffer(1024)
        self.u.GetWindowTextW(hwnd, buffer, 1024)
        return buffer.value

    def process_name(self, hwnd):
        pid = self.w.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, self.c.byref(pid))
        handle = self.k.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return ""
        buffer, size = self.c.create_unicode_buffer(1024), self.w.DWORD(1024)
        self.k.QueryFullProcessImageNameW(handle, 0, buffer, self.c.byref(size))
        self.k.CloseHandle(handle)
        return Path(buffer.value).name.casefold()

    def control_text(self, hwnd):
        length = self.u.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
        buffer = self.c.create_unicode_buffer(length + 1)
        self.u.SendMessageW(hwnd, WM_GETTEXT, length + 1, self.c.addressof(buffer))
        return buffer.value

    def set_text(self, hwnd, text):
        buffer = self.c.create_unicode_buffer(text)
        self.u.SendMessageW(hwnd, WM_SETTEXT, 0, self.c.addressof(buffer))

    def post_key(self, hwnd, key):
        scan = self.u.MapVirtualKeyW(key, 0)
        self.u.PostMessageW(hwnd, WM_KEYDOWN, key, 1 | (scan << 16))
        time.sleep(0.03)
        self.u.PostMessageW(hwnd, WM_KEYUP, key, self.c.c_ssize_t(1 | (scan << 16) | 0xC0000000).value)


def run(request, win):
    started = time.monotonic()

    def done(status, reason=None, dispatched=False, **extra):
        return {"status": status, "reason": reason, "dispatchAttempted": dispatched,
                "elapsedMs": round((time.monotonic() - started) * 1000, 1), **extra}

    windows = [(win.title(h), h) for h in win.top_windows() if win.process_name(h) == PROCESS]
    if not windows:
        return done("blocked", "app_not_running")
    if request.get("action") == "windows":
        return done("ok", items=[{"windowTitle": name} for name, _ in windows])
    name = request.get("windowTitle")
    if not isinstance(name, str) or not name.strip():
        return done("failed", "window_title_required")
    matches = [h for title, h in windows if title == name]
    if len(matches) != 1:
        return done("blocked", "target_window_not_open" if not matches else "duplicate_window_title")

    def unique(cls):
        found = [h for h in win.descendants(matches[0]) if win.class_name(h).upper() == cls.upper()]
        return found[0] if len(found) == 1 else None

    if request["action"] == "read_text":
        control = unique(TEXT_CLASS)
        return done("ok", text=win.control_text(control)) if control else done("blocked", "text_control_not_unique")
    if request["action"] == "submit":
        text = request.get("text")
        if not isinstance(text, str) or not text.strip():
            return done("failed", "text_required")
        composer = unique(COMPOSER_CLASS)
        if not composer:
            return done("blocked", "composer_not_unique")
        if win.control_text(composer):
            return done("blocked", "existing_draft_preserved")
        win.set_text(composer, text.replace("\r\n", "\n").replace("\n", "\r\n"))
        if win.control_text(composer).replace("\r\n", "\n") != text.replace("\r\n", "\n"):
            win.set_text(composer, "")
            return done("blocked", "composer_text_mismatch")
        win.post_key(composer, VK_RETURN)  # The only dispatch point. Never retried here.
        return done("dispatched", dispatched=True)
    return done("failed", "unknown_action")


def main():
    if sys.platform != "win32":
        print(json.dumps({"status": "blocked", "reason": "windows_required", "dispatchAttempted": False}))
        return 1
    request = json.loads(sys.stdin.read() or "{}")
    result = run(request, Win32())
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in ("ok", "dispatched") else 1


if __name__ == "__main__":
    raise SystemExit(main())
