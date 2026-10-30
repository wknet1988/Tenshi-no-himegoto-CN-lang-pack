#!/usr/bin/env python3
"""
play3.py — 真实鼠标输入 + 逐帧截图，用于验证中文渲染
  python play3.py <dir> [wait] [n_clicks] [outdir]
"""
import ctypes, ctypes.wintypes as wt, subprocess, sys, os, time, struct, zlib

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
SW_RESTORE = 9
PW_RENDERFULLCONTENT = 0x00000002


class BMIH(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


def find_lcse():
    res = []

    def cb(h, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(h, c, 100)
        if c.value == 'LCSE':
            r = wt.RECT()
            u32.GetWindowRect(h, ctypes.byref(r))
            res.append((h, r))
        return True
    u32.EnumWindows(EW(cb), None)
    return res


def shot(hwnd, path):
    """DirectX 窗口用 BitBlt 抓取（PrintWindow 对 D3D 表面返回黑屏）"""
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    ok = g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
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
    return (w, h, ok)


def real_click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.25)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.09)
    u32.mouse_event(0x0004, 0, 0, 0, 0)


def main():
    d = sys.argv[1]
    wait = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    out = sys.argv[4] if len(sys.argv) > 4 else '.work/play'
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(wait)
    ws = find_lcse()
    if not ws:
        print('no window'); p.kill(); return
    hwnd, r = ws[0]
    u32.ShowWindow(hwnd, SW_RESTORE)
    u32.SetForegroundWindow(hwnd)
    u32.BringWindowToTop(hwnd)
    time.sleep(1.2)
    tb = r.bottom - r.top - 600      # 标题栏+边框高度
    print('rect', r.left, r.top, r.right, r.bottom, 'titlebar~', tb)
    shot(hwnd, os.path.join(out, '00_title.png'))
    real_click(r.left + 68, r.top + tb + 185)
    time.sleep(4)
    shot(hwnd, os.path.join(out, '01_after_start.png'))
    for i in range(n):
        real_click((r.left + r.right) // 2, r.top + tb + int(600 * 0.88))
        time.sleep(1.3)
        shot(hwnd, os.path.join(out, f'{i+2:02d}.png'))
    p.kill()
    # 报告唯一画面数
    import hashlib
    hs = {}
    for f in sorted(os.listdir(out)):
        hs.setdefault(hashlib.md5(open(os.path.join(out, f), 'rb').read()).hexdigest()[:8], []).append(f)
    print('distinct frames:', len(hs))
    for k, v in hs.items():
        print('  ', k, len(v), v[:3])


if __name__ == '__main__':
    main()