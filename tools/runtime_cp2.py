#!/usr/bin/env python3
"""runtime_cp2.py - poll codepage globals over time to see when CP_TEXT is set"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import os
import time
import struct

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

VM_READ = 0x0010
VM_WRITE = 0x0020
VM_OP = 0x0008
QUERY = 0x0400

CP_TEXT = 0x4a63ac
CP_OTHER = 0x4a63b0
CP_GLOBAL = 0x4a66d4


def find_lcse(pid):
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            r = wt.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            w = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(w))
            res.append((h, r, w.value))
        return True

    u32.EnumWindows(EW(cb), None)
    return res


def read32(hp, a):
    b = (ctypes.c_char * 4)()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(a), b, 4, None):
        return None
    return struct.unpack('<i', b.raw)[0]


def click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.2)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    d = sys.argv[1]
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(11)
    ws = find_lcse(p.pid)
    if not ws:
        print('no window')
        return
    hwnd, r, _ = ws[0]
    u32.ShowWindow(hwnd, 9)
    u32.SetForegroundWindow(hwnd)
    u32.BringWindowToTop(hwnd)
    time.sleep(0.8)
    hp = k32.OpenProcess(VM_READ | VM_WRITE | VM_OP | QUERY, False, p.pid)
    tb = r.bottom - r.top - 600

    def snap(tag):
        print('%-14s TEXT=%-6s OTHER=%-6s GLOBAL=%s' % (
            tag, read32(hp, CP_TEXT), read32(hp, CP_OTHER), read32(hp, CP_GLOBAL)))

    snap('title')
    # 点开始
    for gx in (60, 75, 90, 105):
        click(r.left + gx, r.top + tb + 180)
        time.sleep(0.7)
    snap('after-start')
    for i in range(6):
        click((r.left + r.right) // 2, r.top + tb + int(600 * 0.88))
        time.sleep(0.9)
        snap('click%d' % i)
    k32.CloseHandle(hp)
    try:
        p.kill()
    except Exception:
        pass


if __name__ == '__main__':
    main()