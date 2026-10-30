#!/usr/bin/env python3
"""
peek_mem.py — 读取运行中游戏进程的内存，验证 codepage 与编码表选择
  用法: python peek_mem.py <game_dir>
"""
import ctypes, ctypes.wintypes as wt, subprocess, sys, os, time, struct

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wt.DWORD), ('RegionSize', ctypes.c_size_t),
                ('State', wt.DWORD), ('Protect', wt.DWORD), ('Type', wt.DWORD)]


def find_lcse_pid(pid):
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            wpid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(wpid))
            res.append((h, wpid.value))
        return True
    u32.EnumWindows(EW(cb), None)
    return res


def read_mem(hp, addr, size):
    buf = (ctypes.c_char * size)()
    n = k32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, size, None)
    if not n:
        return None
    return buf.raw[:n]


def main():
    d = sys.argv[1]
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(12)
    wins = find_lcse_pid(p.pid)
    print('LCSE windows:', wins, 'pid', p.pid)
    hp = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, p.pid)
    print('OpenProcess ->', hp, 'err', k32.GetLastError())
    if not hp:
        p.kill(); return
    IMG = 0x400000
    checks = {
        'codepage [0x4a66d4]': 0x4a66d4,
        'flag     [0x4a663c]': 0x4a663c,
        'charset  [0x4a675c]': 0x4a675c,
        'other    [0x4a6764]': 0x4a6764,
        'other    [0x4a6760]': 0x4a6760,
    }
    for name, a in checks.items():
        d2 = read_mem(hp, a, 8)
        if d2 and len(d2) >= 4:
            v = struct.unpack('<i', d2[:4])[0]
            print(f'  {name} = {v} (0x{v & 0xffffffff:x})')
        else:
            print(f'  {name} = <unreadable>')
    k32.CloseHandle(hp)
    p.kill()


if __name__ == '__main__':
    main()