#!/usr/bin/env python3
"""
review.py — post-process machine drafts and turn them into shippable text.

The draft engine gets the gist right but leaves three classes of problem:
translation-ese, wrong register, and mangled onomatopoeia. This module applies
the fixes that are safe to do mechanically and then reports what still needs a
human eye, so review effort goes where it matters.

  python review.py scan <NAME>     show the lines most likely to need work
  python review.py build <NAME>    write .work/zh/<NAME>.json for the reviewer
  python review.py approve <NAME>  freeze the reviewed file into .work/zh
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, '.work', 'draft')
ZHDIR = os.path.join(ROOT, '.work', 'zh')

CTRL = '\x01\x02\x03\x04\x05'

# Onomatopoeia the engine reliably mangles. Keep the Japanese: the reader
# expects a scream to look like a scream.
KEEP = [
    'あ', 'ぁ', 'ん', 'っ', 'ゃ', 'ょ', 'ち', 'く', 'う', 'ん',
]
ONOMATOPOEIA = re.compile(
    r'[ぁ-んァ-ヶ]{2,}|[\u3040-\u309f]+ー+')

# Register fixes. "您" from the engine is wrong for a story narrated in
# first person by a brother addressing his sister.
REGISTER = [
    ('您', '你'),
    ('您们', '你们'),
    ('被看见', '被看到'),
    ('被视为', '被当成'),
    ('的的', '的'),
    ('了了', '了'),
    ('，，', '，'),
    ('。。', '。'),
    ('「「', '「'),
    ('」」', '」'),
]


def tidy(text):
    for a, b in REGISTER:
        text = text.replace(a, b)
    text = re.sub(r'\s+([。，、）」])', r'\1', text)
    text = re.sub(r'([（「])\s+', r'\1', text)
    return text


def ctrl_signature(text):
    return sorted(c for c in text if c in CTRL)


def load(name):
    path = os.path.join(DRAFT, name + '.json')
    return json.load(open(path, encoding='utf-8'))


def scan(name):
    data = load(name)
    risky = []
    for k, v in data.items():
        src, draft = v['src'], v['draft']
        issues = []
        if not draft:
            issues.append('EMPTY')
        else:
            if ctrl_signature(src) != ctrl_signature(draft):
                issues.append('CTRL')
            if len(draft) > len(src) * 2.2:
                issues.append('LONG')
            if re.search(r'[A-Za-z]{4,}', draft):
                issues.append('LATIN')
            if ONOMATOPOEIA.search(draft):
                issues.append('ONOMA')
            if 'Kya' in draft or 'ahhh' in draft.lower():
                issues.append('SHOUT')
            if re.search(r'[ぁ-んァ-ヶ]', draft):
                issues.append('KANA-LEFT')
        if issues:
            risky.append((k, issues, src, draft))
    print('%s: %d lines, %d flagged'
          % (name, len(data), len(risky)))
    for k, iss, src, draft in risky[:25]:
        print('  [%s] %s' % (','.join(iss), k))
        print('      src   %s' % src[:58])
        print('      draft %s' % draft[:58])


def build(name):
    """Write a review file: the draft with source alongside, ready to edit."""
    data = load(name)
    out = {}
    for k, v in data.items():
        draft = tidy(v['draft']) if v['draft'] else ''
        out[k] = {'src': v['src'], 'draft': draft}
    path = os.path.join(DRAFT, name + '.review.json')
    json.dump(out, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('wrote %s (%d lines)' % (path, len(out)))


def approve(name):
    """Copy a reviewed file into .work/zh, dropping empty drafts so the line
    keeps its original Japanese."""
    src = os.path.join(DRAFT, name + '.review.json')
    if not os.path.exists(src):
        print('!! run review.py build %s first' % name)
        return 0
    data = json.load(open(src, encoding='utf-8'))
    out = {}
    for k, v in data.items():
        text = v['draft'].strip() if isinstance(v, dict) else str(v).strip()
        if not text:
            continue
        out[k] = text
    dst = os.path.join(ZHDIR, name + '.json')
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%s: approved %d lines (kept Japanese for %d)'
          % (name, len(out), len(data) - len(out)))
    return len(out)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'scan':
        scan(name)
    elif cmd == 'build':
        build(name)
    elif cmd == 'approve':
        approve(name)
    else:
        print(__doc__)
        raise SystemExit(1)