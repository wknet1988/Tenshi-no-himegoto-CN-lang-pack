#!/usr/bin/env python3
"""
play.py — 自动点击推进剧情并截图，验证中文文本渲染
  python play.py <dir> [wait] [click_x_frac] [click_y_frac] [n_clicks] [outdir]
"""
import ctypes, ctypes.wintypes as wt, subprocess, sys, os, time, struct, zlib

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


class BMIH(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


def shot(hwnd, path):
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH); bi.biWidth = w; bi.biHeight = -h
    bi.biPlanes = 1; bi.biBitCount = 32; bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    row = (w * 3 + 3) // 4 * 4
    px = bytearray(row * h)
    raw = buf.raw
    for y in range(h):
        si = y * w * 4; di = y * row
        for xx in range(w):
            px[di + xx * 3] = raw[si + 2]
            px[di + xx * 3 + 1] = raw[si + 1]
            px[di + xx * 3 + 2] = raw[si]
            si += 4
    hdr = b'BM' + struct.pack('<IHHI', 14 + len(px), 0, 0, 54)
    info = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, len(px), 2835, 2835, 0, 0)
    bmpdata = hdr + info + bytes(px)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)

    # 直接写 PNG
    rawpng = bytearray()
    for y in range(h):
        line = bmpdata[54 + y * row: 54 + y * row + w * 3]
        rawpng += b'\x00' + bytes(b for x in range(w)
                                 for b in (line[x * 3 + 2], line[x * 3 + 1], line[x * 3]))

    def chunk(t, data):
        c = t + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(rawpng), 6)) + chunk(b'IEND', b''))
    open(path, 'wb').write(png)
    return (w, h)


def click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    d = sys.argv[1]
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    fx = float(sys.argv[3]) if len(sys.argv) > 3 else 0.115
    fy = float(sys.argv[4]) if len(sys.argv) > 4 else 0.42
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 10
    out = sys.argv[6] if len(sys.argv) > 6 else '.work/shots'
    os.makedirs(out, exist_ok=True)
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(wait)
    ws = find_lcse()
    if not ws:
        print('no window'); p.kill(); return
    hwnd, (L, T, R, B) = ws[0]
    print('rect', (L, T, R, B))
    shot(hwnd, os.path.join(out, 'p00_title.png'))
    # 点开始游戏
    click(L + (R - L) * fx, T + (B - T) * fy)
    time.sleep(3)
    shot(hwnd, os.path.join(out, 'p01_start.png'))
    # 推进
    for i in range(n):
        click((L + R) // 2, T + (B - T) * 0.86)
        time.sleep(1.0)
        shot(hwnd, os.path.join(out, f'p{i+2:02d}.png'))
    p.kill()
    print('done ->', out)


if __name__ == '__main__':
    main()