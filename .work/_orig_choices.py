# -*- coding: utf-8 -*-
"""从原版 tenshi 包直读脚本，打印指定字符串；并打印选择枝的字符串下标。"""
import os, sys, struct
sys.path.insert(0, 'tools')
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script

recs = parse_lst('tenshi/lcsebody.lst')
body = open('tenshi/lcsebody', 'rb').read()


def load(nm):
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else body[r['offset']:r['offset'] + r['size']]
    return Script(raw, encoding='cp932')


def args(o, k):
    b = o.inst[k * 12:(k + 1) * 12]
    return b[0], struct.unpack('<i', b[4:8])[0], struct.unpack('<i', b[8:12])[0]


for nm in sys.argv[1:]:
    o = load(nm)
    print('==', nm, 'strings', len(o.strings))
    for i in range(o.count):
        op, a1, a2 = args(o, i)
        if op != 0x10 or a1 != 3 or a2 != 0:
            continue
        for j in range(i + 1, min(o.count, i + 12)):
            op2, a12, a22 = args(o, j)
            if op2 == 0x11 and a12 == 2 and a22 in o.offset_of:
                k = o.offset_of[a22]
                print('  inst@%d  str#%d  %s' % (i, k, repr(o.strings[k])))
            elif op2 == 0x11 and a12 == 0:
                continue
            else:
                break
