# -*- coding: utf-8 -*-
"""审计全包选择枝（正确签名：op=0x10 且 arg1==3 且 arg2==0）。"""
import os, sys, struct, json
sys.path.insert(0, 'tools')
from lcse_script import Script

zh = {}
for f in os.listdir('.work/zh_backup'):
    if f.endswith('.json'):
        zh[f[:-5]] = json.load(open(os.path.join('.work/zh_backup', f), encoding='utf-8'))


def args(o, k):
    b = o.inst[k * 12:(k + 1) * 12]
    return b[0], struct.unpack('<i', b[4:8])[0], struct.unpack('<i', b[8:12])[0]


rows = []
for name in sorted(os.listdir('.work/extract')):
    p = os.path.join('.work/extract', name)
    if not os.path.isfile(p):
        continue
    try:
        o = Script(open(p, 'rb').read(), encoding='cp932')
    except Exception:
        continue
    for i in range(o.count):
        op, a1, a2 = args(o, i)
        if op != 0x10 or a1 != 3 or a2 != 0:
            continue
        opts = []
        for j in range(i + 1, min(o.count, i + 12)):
            op2, a12, a22 = args(o, j)
            if op2 == 0x11 and a12 == 2 and a22 in o.offset_of:
                k = o.offset_of[a22]
                opts.append((k, o.strings[k]))
            elif op2 == 0x11 and a12 == 0:
                continue
            else:
                break
        rows.append((name, i, opts))

print('全包选择枝处数:', len(rows))
tot = miss = 0
for name, at, opts in rows:
    d = zh.get(name, {})
    parts = []
    ok = 0
    for k, txt in opts:
        tot += 1
        key = '%s#%d' % (name, k)
        hit = key in d
        ok += 1 if hit else 0
        miss += 0 if hit else 1
        parts.append('%s%s' % (txt[:24].replace('\x01', '|'), '' if hit else '【未译】'))
    print('%-9s @%-5d %d/%d  %s' % (name, at, ok, len(opts), ' | '.join(parts)))
print('选项标签合计 %d | 已译 %d | 未译 %d' % (tot, tot - miss, miss))
