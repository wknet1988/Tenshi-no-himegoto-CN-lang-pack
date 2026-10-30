"""Does GetGlyphOutlineA accept Unicode code points from this engine's path?"""
import ctypes
import ctypes.wintypes as wt

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32


class LOGFONT(ctypes.Structure):
    _fields_ = [('lfHeight', ctypes.c_long), ('lfWidth', ctypes.c_long),
                ('lfEscapement', ctypes.c_long), ('lfOrientation', ctypes.c_long),
                ('lfWeight', ctypes.c_long), ('lfItalic', ctypes.c_byte),
                ('lfUnderline', ctypes.c_byte), ('lfStrikeOut', ctypes.c_byte),
                ('lfCharSet', ctypes.c_byte), ('lfOutPrecision', ctypes.c_byte),
                ('lfClipPrecision', ctypes.c_byte), ('lfQuality', ctypes.c_byte),
                ('lfPitchAndFamily', ctypes.c_byte), ('lfFaceName', ctypes.c_byte * 32)]


class MAT2(ctypes.Structure):
    _fields_ = [('ef', ctypes.c_ulonglong), ('scaled', ctypes.c_ulonglong)]


g32.GetGlyphOutlineA.restype = ctypes.c_int
g32.GetGlyphOutlineA.argtypes = [wt.HDC, wt.UINT, wt.UINT, ctypes.c_void_p,
                                 ctypes.c_void_p, ctypes.c_int, wt.DWORD, ctypes.c_void_p]

buf = ctypes.create_string_buffer(65536)

if __name__ == '__main__':
    text = '闭上眼睛'
    for cs, name in ((128, 'SHIFTJIS'), (134, 'GB2312')):
        lf = LOGFONT()
        lf.lfHeight = -32
        lf.lfWeight = 400
        lf.lfCharSet = cs
        lf.lfQuality = 2
        lf.lfFaceName[:6] = b'SimSun'
        h = g32.CreateFontIndirectA(ctypes.byref(lf))
        hdc = u32.GetDC(0)
        old = g32.SelectObject(hdc, h)
        mat = MAT2()
        print('charset=%d (%s) via Unicode code point:' % (cs, name))
        for ch in text:
            n = g32.GetGlyphOutlineA(hdc, ord(ch), 0, ctypes.byref(mat),
                                     buf, 65536, 0, None)
            print('   %s U+%04X -> %d bytes  %s'
                  % (ch, ord(ch), n, 'glyph' if n > 0 else 'MISSING'))
        g32.SelectObject(hdc, old)
        u32.ReleaseDC(0, hdc)
        g32.DeleteObject(h)
        print()
