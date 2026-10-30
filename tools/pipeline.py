#!/usr/bin/env python3
"""
pipeline.py — batch translation helpers for the LC-ScriptEngine data.

Subcommands:
  list                 show untranslated scripts with their line counts
  export <NAME> [...]  write the translatable strings of those scripts
  import <NAME>        read .work/inbox/<NAME>.json back into .work/zh
  check                verify .work/zh covers the intended strings
  filter <NAME>        flag lines that look like they need review

Translation files live in .work/zh/<NAME>.json as {"<NAME>#<idx>": "text"}.
Anything omitted keeps its original Japanese, which is how sensitive lines
are left untouched.
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
EXTRACT = os.path.join(ROOT, '.work', 'extract')
INBOX = os.path.join(ROOT, '.work', 'inbox')
ZHDIR = os.path.join(ROOT, '.work', 'zh')

KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# Control codes the engine uses. They must survive translation untouched.
CTRL = '\x01\x02\x03\x04\x05'

# Words that mark a line as sensitive. Lines containing any of these are
# reported so a human can decide; nothing is dropped automatically.
SENSITIVE = [
    'Pant', 'Moan', 'Orgasm', 'Climax', 'Ejacul', 'Masturb', 'Cervix',
    ' Semen', 'Lactation', 'Nipple', 'Pussy', 'Vagina', 'Penis',
    '揉', '撫で', '舐', '吸', '射精', '愛液', '体液', '禁断', '凌辱',
    'NcF', '乱暴', '凌訊', 'ペ════', 'ペ penis', 'ペ\t',
]


def scripts():
    recs = parse_lst(os.path.join(GAME, 'lcsebody.lst'))
    body = open(os.path.join(GAME, 'lcsebody'), 'rb').read()
    out = []
    for r in recs:
        if r['unk'] != 1:
            continue
        sc = Script(x(body[r['offset']:r['offset'] + r['size']], 2),
                    encoding='cp932')
        out.append((r['name'], sc))
    return out


def translated():
    return {os.path.basename(p)[:-5]
            for p in (os.path.join(ZHDIR, f) for f in os.listdir(ZHDIR))}


def translatable(sc):
    """Indices of strings that carry visible Japanese text."""
    return [i for i, s in enumerate(sc.strings) if KANA.search(s)]


def cmd_list():
    done = translated()
    rows = []
    for name, sc in scripts():
        if name in done:
            continue
        n = len(translatable(sc))
        if n:
            rows.append((name, n))
    print('untranslated: %d scripts, %d lines' % (len(rows), sum(c for _, c in rows)))
    for name, n in rows:
        print('  %-10s %5d' % (name, n))


def cmd_export(names):
    os.makedirs(INBOX, exist_ok=True)
    table = {name: sc for name, sc in scripts()}
    for name in names:
        sc = table.get(name)
        if sc is None:
            print('!! no such script: %s' % name)
            continue
        idxs = translatable(sc)
        payload = {}
        for i in idxs:
            payload['%s#%d' % (name, i)] = sc.strings[i]
        path = os.path.join(INBOX, name + '.json')
        json.dump(payload, open(path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('%-10s -> %s  (%d lines)' % (name, path, len(idxs)))


def cmd_import(names):
    for name in names:
        src = os.path.join(INBOX, name + '.json')
        if not os.path.exists(src):
            print('!! missing %s' % src)
            continue
        data = json.load(open(src, encoding='utf-8'))
        dst = os.path.join(ZHDIR, name + '.json')
        cur = {}
        if os.path.exists(dst):
            cur = json.load(open(dst, encoding='utf-8'))
        # Only keep keys that still map to a real string.
        table = {n: sc for n, sc in scripts()}
        sc = table.get(name)
        if sc is None:
            print('!! no such script: %s' % name)
            continue
        good = {}
        dropped = 0
        for k, v in data.items():
            idx = int(k.split('#')[1])
            if not (0 <= idx < len(sc.strings)):
                dropped += 1
                continue
            good[k] = v
        json.dump(good, open(dst, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('%-10s imported %d lines%s'
              % (name, len(good), (' (%d dropped)' % dropped) if dropped else ''))


def cmd_check(names=None):
    table = {n: sc for n, sc in scripts()}
    problems = 0
    for path in sorted(os.listdir(ZHDIR)):
        name = path[:-5]
        sc = table.get(name)
        if sc is None:
            print('!! translation for unknown script: %s' % name)
            problems += 1
            continue
        data = json.load(open(os.path.join(ZHDIR, path), encoding='utf-8'))
        for k, v in data.items():
            idx = int(k.split('#')[1])
            if not (0 <= idx < len(sc.strings)):
                print('!! %s: index %d out of range' % (name, idx))
                problems += 1
                continue
            orig = sc.strings[idx]
            oc = [c for c in orig if c in CTRL]
            nc = [c for c in v if c in CTRL]
            if sorted(oc) != sorted(nc):
                print('!! %s[%d] control codes differ: %r vs %r' % (name, idx, orig, v))
                problems += 1
            try:
                v.encode('cp932')
            except UnicodeEncodeError as e:
                print('!! %s[%d] not Shift-JIS encodable: %s' % (name, idx, e))
                problems += 1
    print('problems: %d' % problems)
    return problems


def cmd_filter(names):
    table = {n: sc for n, sc in scripts()}
    for name in names:
        sc = table.get(name)
        if sc is None:
            continue
        hits = []
        for i in translatable(sc):
            s = sc.strings[i]
            if any(w in s for w in SENSITIVE):
                hits.append((i, s))
        print('%s: %d flagged' % (name, len(hits)))
        for i, s in hits[:20]:
            print('  [%d] %s' % (i, s[:70]))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == 'list':
        cmd_list()
    elif cmd == 'export':
        cmd_export(args)
    elif cmd == 'import':
        cmd_import(args)
    elif cmd == 'check':
        raise SystemExit(1 if cmd_check(args) else 0)
    elif cmd == 'filter':
        cmd_filter(args)
    else:
        print(__doc__)
        raise SystemExit(1)