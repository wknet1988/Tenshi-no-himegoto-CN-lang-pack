#!/usr/bin/env python3
"""runtime_cp.py - read/patch codepage globals in a running game process"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import os
import time
import struct

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

VM_READ = 0x0010
VM_WRITE = 0x0020
VM_OP = 0x0008
QUERY = 0x0400

CP_TEXT = 0x4a63ac
CP_OTHER = 0x4a63b0
CP_GLOBAL = 0x4a66d4


def find_lcse_pid(pid):
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            w = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(w))
            res.append((h, w.value))
        return True

    u32.EnumWindows(EW(cb), None)
    return res


def read32(hp, addr):
    buf = (ctypes.c_char * 4)()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, 4, None):
        return None
    return struct.unpack('<i', buf.raw)[0]


def write32(hp, addr, val):
    data = struct.pack('<i', val)
    buf = (ctypes.c_char * 4).from_buffer_copy(data)
    return k32.WriteProcessMemory(hp, ctypes.c_void_p(addr), buf, 4, None)


def main():
    d = sys.argv[1]
    cp = int(sys.argv[2]) if len(sys.argv) > 2 else 936
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(10)
    wins = find_lcse_pid(p.pid)
    print('LCSE windows:', wins)
    hp = k32.OpenProcess(VM_READ | VM_WRITE | VM_OP | QUERY, False, p.pid)
    err = k32.GetLastError()
    print('OpenProcess ->', hp, 'err', err)
    if not hp:
        try:
            p.kill()
        except Exception:
            pass
        return
    addrs = [('CP_TEXT', CP_TEXT), ('CP_OTHER', CP_OTHER), ('CP_GLOBAL', CP_GLOBAL)]
    print('--- before ---')
    for name, a in addrs:
        print('  %-9s %s' % (name, read32(hp, a)))
    print('--- write %d ---' % cp)
    for name, a in addrs:
        r = write32(hp, a, cp)
        print('  %-9s wrote=%s now=%s' % (name, r, read32(hp, a)))
    k32.CloseHandle(hp)
    time.sleep(1)
    try:
        p.kill()
    except Exception:
        pass


if __name__ == '__main__':
    main()