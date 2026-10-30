#!/usr/bin/env python3
"""
to_jp.py -- rewrite the translation into glyphs the original engine can draw.

The engine walks string bytes with Shift-JIS rules and asks GDI for glyphs by
byte value, so a simplified character whose Shift-JIS encoding is not a legal
lead/trail pair desynchronises the walk and the line renders as noise.

Roughly two thirds of the translation already encodes cleanly. The rest is
mapped onto a traditional or Japanese glyph that does. A traditional form is
preferred over a merely synonymous character: a reader who sees 這 rather than
此 recognises the intended character far more readily. Particles have no
usable kanji form, so they become kana.

The mapping lives in .work/glyph_map.json so new characters can be added
without touching this file.

  python tools/to_jp.py            report coverage
  python tools/to_jp.py --apply    rewrite .work/zh/*.json in place
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZHDIR = os.path.join(ROOT, '.work', 'zh')
MAP = os.path.join(ROOT, '.work', 'glyph_map.json')


def drawable(ch):
    """True when Shift-JIS can encode this character as a legal pair."""
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    return len(b) == 2


def usable(v):
    """True when a replacement *string* is safe to emit.

    Japanese often needs several kana for what Chinese writes with one
    character (拟声词/语气助词/人称代词), e.g. 啦 -> よ, 嘻 -> くす,
    咕 -> く, 砰 -> バタン, 她 -> 彼女. So a replacement may be more than one
    character -- as long as every character stays a legal Shift-JIS pair the
    engine's byte walk keeps its alignment.
    """
    if not isinstance(v, str) or not v:
        return False
    return all(drawable(c) for c in v)


def load_map():
    with open(MAP, encoding='utf-8') as f:
        raw = json.load(f)
    out = {}
    for k, v in raw.items():
        if len(k) != 1:
            continue            # keys must be single characters
        if usable(v):           # value may be one character or several kana
            out[k] = v
    return out


MERGED = load_map()


def convert(text):
    out = []
    for ch in text:
        if drawable(ch):
            out.append(ch)
            continue
        rep = MERGED.get(ch)
        if rep:
            out.append(rep)
            continue
        # Control codes and ASCII pass through; anything unmapped becomes a
        # middle dot so no byte escapes the Shift-JIS range.
        if ord(ch) < 0x80:
            out.append(ch)
        else:
            out.append('\u30fb')
    return ''.join(out)


def _scan():
    chars = set()
    for p in sorted(glob.glob(os.path.join(ZHDIR, '*.json'))):
        for v in json.load(open(p, encoding='utf-8')).values():
            for ch in v:
                if '\u4e00' <= ch <= '\u9fff':
                    chars.add(ch)
    return chars


def report():
    chars = _scan()
    direct = [c for c in chars if drawable(c)]
    mapped = [c for c in chars
              if not drawable(c) and c in MERGED]
    lost = sorted(c for c in chars
                  if not drawable(c) and c not in MERGED)
    print('distinct hanzi : %d' % len(chars))
    print('  encodable    : %d' % len(direct))
    print('  mapped       : %d' % len(mapped))
    print('  unrecoverable: %d' % len(lost))
    if lost:
        for i in range(0, len(lost), 40):
            print('  ' + ''.join(lost[i:i + 40]))
    return lost


def apply():
    lost = report()
    print()
    changed = 0
    for p in sorted(glob.glob(os.path.join(ZHDIR, '*.json'))):
        data = json.load(open(p, encoding='utf-8'))
        new = {}
        for k, v in data.items():
            nv = convert(v)
            if nv != v:
                changed += 1
            new[k] = nv
        json.dump(new, open(p, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print('rewrote %d entries' % changed)


if __name__ == '__main__':
    if '--apply' in sys.argv:
        apply()
    else:
        report()
