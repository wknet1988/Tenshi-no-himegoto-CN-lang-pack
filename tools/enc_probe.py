"""Find a byte encoding for Chinese that survives the engine's SJIS traversal.

The engine walks string bytes with Shift-JIS rules: 0x81-0x9F and 0xE0-0xFC are
lead bytes, 0x40-0x7E / 0x80-0xFC are trails. A Chinese character stored as
GBK has a lead byte in 0xB0-0xD7, which Shift-JIS treats as a single-byte
character, so the walk desynchronises.

The fix: pick byte pairs that are BOTH valid GBK (so the renderer maps them to
the right glyph) AND form a legal Shift-JIS lead/trail pair (so the walk stays
in sync). Candidates are searched exhaustively below.
"""
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

SJIS_LEAD = [(0x81, 0x9F), (0xE0, 0xFC)]
SJIS_TRAIL = [(0x40, 0x7E), (0x80, 0xFC)]


def sjis_lead(b):
    return any(lo <= b <= hi for lo, hi in SJIS_LEAD)


def sjis_trail(b):
    return any(lo <= b <= hi for lo, hi in SJIS_TRAIL)


def sjis_walk(data):
    """Split bytes the way the engine does. Returns list of character groups."""
    out = []
    i = 0
    while i < len(data):
        c = data[i]
        if i + 1 < len(data) and sjis_lead(c) and sjis_trail(data[i + 1]):
            out.append(data[i:i + 2])
            i += 2
        else:
            out.append(data[i:i + 1])
            i += 1
    return out


def gbk_chars():
    """Yield (char, gbk_bytes) for every character GBK can encode."""
    for cp in range(0x20, 0xFF00):
        ch = chr(cp)
        try:
            b = ch.encode('gbk')
        except UnicodeEncodeError:
            continue
        if len(b) == 2:
            yield ch, b


if __name__ == '__main__':
    # Which GBK characters survive an SJIS walk without breaking alignment?
    good = []
    for ch, b in gbk_chars():
        groups = sjis_walk(b)
        if len(groups) == 1 and len(groups[0]) == 2:
            good.append((ch, b))
    print('GBK chars whose bytes stay aligned under SJIS rules: %d' % len(good))

    # Sample the common Chinese characters we actually need.
    need = '的一是不了人我在有他这为之大来以个中上们到说国和地也子时道出而要于就下得可你年生自会那后能对着事其里所去行过家十用发天如然作方成者多日都三小军二无同么经法当起与好看学进种将还分此心前面又定见只主没公从闭眼现远张脸浮现同一祝福'
    usable = {ch for ch, _ in good}
    ok = [c for c in need if c in usable]
    bad = [c for c in need if c not in usable]
    print('needed chars: %d, usable: %d, NOT usable: %d'
          % (len(set(need)), len(set(ok)), len(set(bad))))
    print('not usable:', ''.join(sorted(set(bad))))
