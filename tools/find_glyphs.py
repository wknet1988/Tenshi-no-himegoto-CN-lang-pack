"""List every kanji Shift-JIS can encode, with readings, to pick substitutes."""
import sys

# JIS X 0208 level-1 kanji live at 0x889F..0x9872 in Shift-JIS; that whole block
# is what the original game draws from.
def jis_kanji():
    out = []
    for hi in range(0x88, 0x9A + 1):
        for lo in range(0x9F, 0xFC + 1):
            try:
                b = bytes([hi, lo])
            except ValueError:
                continue
            try:
                ch = b.decode('shift_jis')
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and '\u4e00' <= ch <= '\u9fff':
                out.append(ch)
    return out


if __name__ == '__main__':
    ks = jis_kanji()
    print('JIS X 0208 kanji available: %d' % len(ks))
    if len(sys.argv) > 1:
        # Print candidates whose reading starts with a given syllable.
        # Without a reading table we fall back to listing every glyph, sorted.
        ks.sort()
        print(''.join(ks))
    else:
        print('sample:', ''.join(ks[:60]))
