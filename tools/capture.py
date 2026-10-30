#!/usr/bin/env python3
"""
capture.py — 启动游戏并截取 LCSE 窗口像素，验证中文渲染
  python capture.py <dir> [wait_seconds]
"""
import ctypes, ctypes.wintypes as wt, subprocess, sys, os, time, struct

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))


def find_lcse():
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            r = wt.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            res.append((h, (r.left, r.top, r.right, r.bottom)))
        return True

    u32.EnumWindows(EW(cb), None)
    return res


def save_bmp(hwnd, path):
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        print('bad size', w, h)
        return None
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    SRCCOPY = 0x00CC0020
    g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, SRCCOPY)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                    ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                    ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                    ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                    ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = w
    bi.biHeight = -h          # 负高度 = 自上而下
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

    row = (w * 3 + 3) // 4 * 4
    pixels = bytearray(row * h)
    raw = buf.raw
    for y in range(h):
        si = y * w * 4
        di = y * row
        for x in range(w):
            b, g, rr = raw[si], raw[si + 1], raw[si + 2]
            pixels[di + x * 3] = rr
            pixels[di + x * 3 + 1] = g
            pixels[di + x * 3 + 2] = b
            si += 4
    hdr = b'BM' + struct.pack('<IHHI', 14 + len(pixels), 0, 0, 54)
    info = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    open(path, 'wb').write(hdr + info + bytes(pixels))
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    return (w, h)


def main():
    d, secs = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12
    outdir = sys.argv[3] if len(sys.argv) > 3 else '.work/shots'
    os.makedirs(outdir, exist_ok=True)
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(secs)
    ws = find_lcse()
    if not ws:
        print('LCSE window not found')
        p.kill()
        return
    hwnd, rect = ws[0]
    print('LCSE rect', rect)
    print('shot1', save_bmp(hwnd, os.path.join(outdir, 'shot1.bmp')))
    # 发送鼠标点击推进剧情
    cx, cy = (rect[0] + rect[2]) // 2, rect[1] + int((rect[3] - rect[1]) * 0.85)
    for i in range(2, 9):
        u32.SetCursorPos(cx, cy)
        u32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
        u32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
        time.sleep(1.2)
        print(f'shot{i}', save_bmp(hwnd, os.path.join(outdir, f'shot{i}.bmp')))
    p.kill()


if __name__ == '__main__':
    main()