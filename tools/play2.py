#!/usr/bin/env python3
"""
play2.py — 激活窗口 + SendMessage 点击推进 + 客户区截图，验证中文文本
  用法: python play2.py <dir> [wait] [n] [outdir]
"""
import ctypes, ctypes.wintypes as wt, subprocess, sys, os, time, struct, zlib

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0201, 0x0202, 0x0001
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_RETURN, VK_SPACE = 0x0D, 0x20


def find_lcse():
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            r = wt.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            res.append((h, (r.right, r.bottom)))
        return True
    u32.EnumWindows(EW(cb), None)
    return res


class BMIH(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


def shot(hwnd, path):
    w0 = wt.RECT(); u32.GetClientRect(hwnd, ctypes.byref(w0))
    w, h = w0.right, w0.bottom
    if w <= 0 or h <= 0:
        return None
    hdc = u32.GetDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH); bi.biWidth = w; bi.biHeight = -h
    bi.biPlanes = 1; bi.biBitCount = 32; bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)

    rawpng = bytearray()
    raw = buf.raw
    for y in range(h):
        si = y * w * 4
        line = bytearray(b'\x00')
        for x in range(w):
            line += bytes((raw[si + 2], raw[si + 1], raw[si]))
            si += 4
        rawpng += line

    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(rawpng), 6)) + chunk(b'IEND', b''))
    open(path, 'wb').write(png)
    return (w, h)


def click(hwnd, x, y):
    lp = (int(y) << 16) | (int(x) & 0xFFFF)
    u32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)
    time.sleep(0.06)
    u32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lp)


def key(hwnd, vk):
    u32.SendMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    u32.SendMessageW(hwnd, WM_KEYUP, vk, 0)


def activate(hwnd):
    u32.ShowWindow(hwnd, 9)
    u32.SetForegroundWindow(hwnd)
    u32.BringWindowToTop(hwnd)
    u32.SetActiveWindow(hwnd)
    time.sleep(0.6)


def main():
    d = sys.argv[1]
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    out = sys.argv[4] if len(sys.argv) > 4 else '.work/play'
    os.makedirs(out, exist_ok=True)
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(wait)
    ws = find_lcse()
    if not ws:
        print('no window'); p.kill(); return
    hwnd, (W, H) = ws[0]
    activate(hwnd)
    print('client', W, H)
    shot(hwnd, os.path.join(out, '00_title.png'))
    click(hwnd, 68, 185)          # はじめから
    time.sleep(3.5)
    shot(hwnd, os.path.join(out, '01_start.png'))
    for i in range(n):
        click(hwnd, W // 2, int(H * 0.88))
        time.sleep(1.1)
        shot(hwnd, os.path.join(out, f'{i+2:02d}.png'))
    p.kill()
    print('done ->', out)


if __name__ == '__main__':
    main()