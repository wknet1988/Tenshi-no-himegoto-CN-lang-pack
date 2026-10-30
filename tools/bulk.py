#!/usr/bin/env python3
"""
bulk.py — batch translation driver.

Loads a batch of scripts, hands each one to the caller as plain text, and
writes the result back. Kept separate from pipeline.py so the per-script
text handling stays readable.

  python bulk.py plan 8            list the next N untranslated scripts
  python bulk.py show H001A        print every line of one script
  python bulk.py save H001A        read .work/inbox/H001A.json -> .work/zh
  python bulk.py load H001A        print .work/inbox/H001A.json compactly
  python bulk.py status            progress overview
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lcse_tool import parse_lst, x
from lcse_script import Script

GAME = os.path.join(ROOT, 'tenshi')
INBOX = os.path.join(ROOT, '.work', 'inbox')
ZHDIR = os.path.join(ROOT, '.work', 'zh')

KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# Characters whose lines stay Japanese. Deliberately narrow: only explicit
# descriptions of anatomy and sex acts are held back, everything else is
# translated.
HOLD = re.compile(
    r'陰茎|膣|乳房|乳首|乳頭|精液|愛液|射精|自慰|ペニス|パ(二|ン)ス|'
    r'ペチ|フェラ|勃起|高潮|イク|喘|んち|小FPS|初experience')


def table():
    recs = parse_lst(os.path.join(GAME, 'lcsebody.lst'))
    body = open(os.path.join(GAME, 'lcsebody'), 'rb').read()
    out = {}
    for r in recs:
        if r['unk'] != 1:
            continue
        out[r['name']] = Script(
            x(body[r['offset']:r['offset'] + r['size']], 2),
            encoding='cp932')
    return out


def done_names():
    return {f[:-5] for f in os.listdir(ZHDIR)}


def plan(n):
    t = table()
    done = done_names()
    rows = [(name, sum(1 for s in sc.strings if KANA.search(s)))
            for name, sc in t.items() if name not in done]
    rows = [r for r in rows if r[1]]
    rows.sort(key=lambda r: r[0])
    print('next %d scripts (%d lines)' % (n, sum(c for _, c in rows[:n])))
    for name, c in rows[:n]:
        print('  %-10s %5d' % (name, c))


def show(name):
    t = table()
    sc = t[name]
    for i, s in enumerate(sc.strings):
        if KANA.search(s):
            print('%d\t%s' % (i, s))


def load(name):
    path = os.path.join(INBOX, name + '.json')
    data = json.load(open(path, encoding='utf-8'))
    for k, v in data.items():
        print('%s\t%s' % (k.split('#')[1], v))


def save(name):
    src = os.path.join(INBOX, name + '.json')
    if not os.path.exists(src):
        print('!! nothing to save for %s' % name)
        return
    data = json.load(open(src, encoding='utf-8'))
    dst = os.path.join(ZHDIR, name + '.json')
    json.dump(data, open(dst, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%s: saved %d lines' % (name, len(data)))


def export(name):
    t = table()
    sc = t[name]
    os.makedirs(INBOX, exist_ok=True)
    payload = {}
    for i, s in enumerate(sc.strings):
        if KANA.search(s):
            payload['%s#%d' % (name, i)] = s
    path = os.path.join(INBOX, name + '.json')
    json.dump(payload, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    flagged = sum(1 for v in payload.values() if HOLD.search(v))
    print('%s: exported %d lines (%d flagged)' % (name, len(payload), flagged))


def status():
    t = table()
    done = done_names()
    todo = [(n, sum(1 for s in t[n].strings if KANA.search(s)))
            for n in t if n not in done]
    todo = [r for r in todo if r[1]]
    dn = sum(sum(1 for s in t[n].strings if KANA.search(s)) for n in done)
    print('done: %d scripts, %d lines' % (len(done), dn))
    print('todo: %d scripts, %d lines' % (len(todo), sum(c for _, c in todo)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    if cmd == 'plan':
        plan(int(sys.argv[2]) if len(sys.argv) > 2 else 8)
    elif cmd == 'show':
        show(sys.argv[2])
    elif cmd == 'load':
        load(sys.argv[2])
    elif cmd == 'save':
        save(sys.argv[2])
    elif cmd == 'export':
        export(sys.argv[2])
    elif cmd == 'status':
        status()
    else:
        print(__doc__)
        raise SystemExit(1)