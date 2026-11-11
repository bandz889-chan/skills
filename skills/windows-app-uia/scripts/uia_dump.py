#!/usr/bin/env python3
"""Dump a Windows app's UI Automation tree or Win32 window-class tree as indented text.

    py uia_dump.py --list-apps
    py uia_dump.py --process notepad.exe --mode uia --depth 8 --values short
    py uia_dump.py --process notepad.exe --mode win32 --depth 8 --values none

uia mode needs `pip install uiautomation`. win32 mode uses only ctypes.
Values can contain personal content; use --values none before sharing output.
"""

import argparse
import sys
from pathlib import Path


def clip(value, mode):
    if mode == "none" or value is None:
        return ""
    value = str(value).replace("\r", " ").replace("\n", " ")
    return value if mode == "full" or len(value) <= 40 else value[:40] + "…"


class Win32:
    def __init__(self):
        import ctypes
        from ctypes import wintypes as w
        self.c, self.w = ctypes, w
        self.u = ctypes.WinDLL("user32", use_last_error=True)
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.PROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, ctypes.c_ssize_t)
        self.u.EnumWindows.argtypes = [self.PROC, ctypes.c_ssize_t]
        self.u.EnumChildWindows.argtypes = [w.HWND, self.PROC, ctypes.c_ssize_t]
        self.u.GetParent.argtypes, self.u.GetParent.restype = [w.HWND], w.HWND
        self.u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.u.SendMessageTimeoutW.argtypes = [w.HWND, w.UINT, ctypes.c_size_t, ctypes.c_ssize_t, w.UINT, w.UINT,
                                               ctypes.POINTER(ctypes.c_size_t)]
        self.k.OpenProcess.restype = w.HANDLE
        self.k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
        for name, args in (("GetClassNameW", [w.HWND, w.LPWSTR, ctypes.c_int]), ("GetWindowTextW", [w.HWND, w.LPWSTR, ctypes.c_int]),
                           ("IsWindowVisible", [w.HWND]), ("MapVirtualKeyW", [w.UINT, w.UINT])):
            getattr(self.u, name).argtypes = args
        self.k.CloseHandle.argtypes = [w.HANDLE]

    def enum(self, parent=None):
        found = []
        callback = self.PROC(lambda hwnd, _: found.append(hwnd) or True)
        if parent is None:
            self.u.EnumWindows(callback, 0)
        else:
            self.u.EnumChildWindows(parent, callback, 0)
        return found

    def children(self, hwnd):
        return [h for h in self.enum(hwnd) if self.u.GetParent(h) == hwnd]

    def cls(self, hwnd):
        buffer = self.c.create_unicode_buffer(256)
        self.u.GetClassNameW(hwnd, buffer, 256)
        return buffer.value

    def text(self, hwnd):
        result = self.c.c_size_t()
        if not self.u.SendMessageTimeoutW(hwnd, 0x000E, 0, 0, 0x0002, 200, self.c.byref(result)):
            return None
        buffer = self.c.create_unicode_buffer(min(result.value, 4000) + 1)
        self.u.SendMessageTimeoutW(hwnd, 0x000D, len(buffer), self.c.addressof(buffer), 0x0002, 200, self.c.byref(result))
        return buffer.value

    def process(self, hwnd):
        pid = self.w.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, self.c.byref(pid))
        handle = self.k.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return pid.value, ""
        buffer, size = self.c.create_unicode_buffer(1024), self.w.DWORD(1024)
        self.k.QueryFullProcessImageNameW(handle, 0, buffer, self.c.byref(size))
        self.k.CloseHandle(handle)
        return pid.value, Path(buffer.value).name.casefold()


def list_apps(win):
    apps = {}
    for hwnd in win.enum():
        if win.u.IsWindowVisible(hwnd):
            pid, name = win.process(hwnd)
            apps.setdefault((name, pid), []).append(clip(win.text(hwnd), "short"))
    for (name, pid), titles in sorted(apps.items()):
        print(f"{name or '?'}  pid={pid}  windows={len(titles)}  {' | '.join(t for t in titles if t)[:120]}")


def dump_win32(win, process, depth, values):
    tops = [h for h in win.enum() if win.u.IsWindowVisible(h) and win.process(h)[1] == process.casefold()]
    if not tops:
        print("app_not_running_or_no_visible_window")
        return 1
    budget = [5000]

    def walk(hwnd, level):
        budget[0] -= 1
        if budget[0] < 0:
            return
        text = clip(win.text(hwnd), values)
        print("  " * level + f"{win.cls(hwnd)}" + (f'  "{text}"' if text else ""))
        if level < depth:
            for child in win.children(hwnd):
                walk(child, level + 1)
    for top in tops:
        walk(top, 0)
    if budget[0] < 0:
        print("node_limit_reached")
    return 0


def dump_uia(win, process, depth, values):
    try:
        import uiautomation as automation
    except ImportError:
        print("uiautomation_package_required: py -m pip install uiautomation")
        return 1
    tops = [h for h in win.enum() if win.u.IsWindowVisible(h) and win.process(h)[1] == process.casefold()]
    if not tops:
        print("app_not_running_or_no_visible_window")
        return 1
    budget = [5000]

    def patterns(control):
        names = []
        for label, getter in (("Invoke", "GetInvokePattern"), ("Value", "GetValuePattern"), ("Text", "GetTextPattern"),
                              ("Scroll", "GetScrollPattern"), ("SelectionItem", "GetSelectionItemPattern")):
            try:
                if getattr(control, getter)():
                    names.append(label)
            except Exception:
                pass
        return names

    def walk(control, level):
        budget[0] -= 1
        if budget[0] < 0:
            return
        value = ""
        if values != "none":
            try:
                value = clip(control.GetValuePattern().Value, values)
            except Exception:
                value = ""
        line = (f"{control.ControlTypeName}  id={control.AutomationId!r}  name={clip(control.Name, values)!r}"
                f"  class={control.ClassName!r}  patterns={','.join(patterns(control))}")
        if not control.IsEnabled:
            line += "  disabled"
        if value:
            line += f"  value={value!r}"
        print("  " * level + line)
        if level < depth:
            for child in control.GetChildren():
                walk(child, level + 1)
    for top in tops:
        walk(automation.ControlFromHandle(top), 0)
    if budget[0] < 0:
        print("node_limit_reached")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list-apps", action="store_true")
    parser.add_argument("--process", help="executable name, e.g. KakaoTalk.exe")
    parser.add_argument("--mode", choices=("uia", "win32"), default="uia")
    parser.add_argument("--depth", type=int, default=8)
    parser.add_argument("--values", choices=("none", "short", "full"), default="short")
    args = parser.parse_args()
    if sys.platform != "win32":
        print("windows_required")
        return 1
    win = Win32()
    if args.list_apps:
        list_apps(win)
        return 0
    if not args.process:
        parser.error("--process or --list-apps is required")
    dump = dump_uia if args.mode == "uia" else dump_win32
    return dump(win, args.process, args.depth, args.values)


if __name__ == "__main__":
    raise SystemExit(main())
