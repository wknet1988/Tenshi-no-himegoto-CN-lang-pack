import sys, os, time, subprocess, ctypes, struct, zlib, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctypes.wintypes as wt
from play3 import find_lcse, real_click
u32 = ctypes.windll.user32; g32 = ctypes.windll.gdi32

class BMIH(ctypes.Structure):
    _fields_ = [('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32), ('biHeight', ctypes.c_int32),
                ('biPlanes', ctypes.c_uint16), ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
                ('biSizeImage', ctypes.c_uint32), ('biX', ctypes.c_int32), ('biY', ctypes.c_int32),
                ('biClrUsed', ctypes.c_uint32), ('biClrImportant', ctypes.c_uint32)]

def cap(hwnd):
    r = wt.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u32.GetDC(0); mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h); g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, h, hdc, r.left, r.top, 0x00CC0020)
    bi = BMIH(); bi.biSize = ctypes.sizeof(BMIH); bi.biWidth = w; bi.biHeight = -h
    bi.biPlanes = 1; bi.biBitCount = 32; bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdc)
    return buf.raw, w, h, r.left, r.top, r.bottom

def png(raw, w, h, path):
    rp = bytearray()
    for y in range(h):
        si = y * w * 4; ln = bytearray(b'\x00')
        for x in range(w):
            ln += bytes((raw[si+2], raw[si+1], raw[si])); si += 4
        rp += ln
    def ck(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ck(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + ck(b'IDAT', zlib.compress(bytes(rp), 6)) + ck(b'IEND', b''))

if __name__ == '__main__':
    d = sys.argv[1]; out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    p = subprocess.Popen([os.path.join(d, 'lcsebody.exe')], cwd=d)
    time.sleep(11)
    hwnd, r = find_lcse()[0]
    u32.ShowWindow(hwnd, 9); u32.SetForegroundWindow(hwnd); u32.BringWindowToTop(hwnd)
    time.sleep(1.0)
    raw0, w, h, L, T, B = cap(hwnd)
    png(raw0, w, h, os.path.join(out, 'base.png'))
    h0 = hashlib.md5(raw0).hexdigest()
    tb = B - T - 600
    print('window', L, T, B, 'tb', tb, 'client', w, h)
    hit = None
    for gy in (165, 175, 185, 195, 205):
        for gx in (45, 60, 75, 90, 105):
            real_click(L + gx, T + tb + gy)
            time.sleep(0.9)
            raw, w2, h2, *_ = cap(hwnd)
            if hashlib.md5(raw).hexdigest() != h0:
                hit = (gx, gy); print('HIT at', gx, gy)
                png(raw, w2, h2, os.path.join(out, 'hit.png'))
                break
        if hit: break
    print('found', hit)
    try: p.kill()
    except Exception: pass
