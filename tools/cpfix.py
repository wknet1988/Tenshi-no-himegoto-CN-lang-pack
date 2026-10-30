#!/usr/bin/env python3
"""
cpfix.py — 启动游戏后持续把编码相关的全局变量钉在指定 codepage，
          用于验证「哪条路径决定了文本解码」

用法: python cpfix.py <game_dir> <cp> [seconds]
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import os
import time
import struct
import threading

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

VM_READ = 0x0010
VM_WRITE = 0x0020
VM_OP = 0x0008
QUERY = 0x0400

# 全部与编码相关的全局变量
VARS = {
    0x4a63ac: 'CP_TEXT',
    0x4a63b0: 'CP_OTHER',
    0x4a639c: 'CP_CRT',
    0x4a66d4: 'CP_GLOBAL',
    0x4a66d8: 'CHARSET?',
}


def find_win(pid):
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            w = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(w))
            if w.value == pid:
                r = wt.RECT()
                u32.GetWindowRect(h, ctypes.byref(r))
                res.append((h, r))
        return True

    u32.EnumWindows(EW(cb), None)
    return res


def read32(hp, a):
    b = (ctypes.c_char * 4)()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(a), b, 4, None):
        return None
    return struct.unpack('<i', b.raw)[0]


def write32(hp, a, v):
    d = struct.pack('<i', v)
    b = (ctypes.c_char * 4).from_buffer_copy(d)
    return k32.WriteProcessMemory(hp, ctypes.c_void_p(a), b, 4, None)


def click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.12)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    u32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    d = sys.argv[1]
    cp = int(sys.argv[2])
    secs = int(sys.argv[3]) if len(sys.argv) > 3 else 40

    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(8)
    ws = find_win(p.pid)
    if not ws:
        print('no window')
        try:
            p.kill()
        except Exception:
            pass
        return
    hwnd, r = ws[0]
    u32.ShowWindow(hwnd, 9)
    u32.SetForegroundWindow(hwnd)
    u32.BringWindowToTop(hwnd)
    hp = k32.OpenProcess(VM_READ | VM_WRITE | VM_OP | QUERY, False, p.pid)
    print('handle', hp)
    tb = r.bottom - r.top - 600

    stop = False

    def pin():
        while not stop:
            for a in VARS:
                write32(hp, a, cp)
            time.sleep(0.05)

    th = threading.Thread(target=pin, daemon=True)
    th.start()

    print('pinned codepage =', cp, ' for', secs, 's')
    for i in range(secs // 2):
        if p.poll() is not None:
            print('exited at', i * 2)
            break
        click((r.left + r.right) // 2, r.top + tb + int(600 * 0.88))
        time.sleep(2)
    stop = True
    time.sleep(0.3)
    print('final:', {VARS[a]: read32(hp, a) for a in VARS})
    k32.CloseHandle(hp)
    try:
        p.kill()
    except Exception:
        pass


if __name__ == '__main__':
    main()