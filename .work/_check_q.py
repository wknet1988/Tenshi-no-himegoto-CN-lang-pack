#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计序章+INIT 脚本中解码出现 '?' 占位符的字符串比例。"""
import os, sys
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script

recs = parse_lst('cn/lcsebody.lst')
body = open('cn/lcsebody', 'rb').read()
names = ['OP001', 'OP002', 'OP003', 'OP004', 'OP005A', 'OP005B', 'OP006', 'INIT', '_LOADATTITLE']
total = q = 0
for nm in names:
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    if not r:
        print('%-14s 未找到' % nm); continue
    blob = body[r['offset']:r['offset'] + r['size']]
    raw = x(blob, XOR_SCRIPT) if r['unk'] == 1 else blob
    sc = Script(raw, encoding='cp932')
    qt = sum(1 for s in sc.strings if '?' in s)
    total += len(sc.strings); q += qt
    print('%-14s 字符串 %4d  含? %3d' % (nm, len(sc.strings), qt))
print('\n序章+INIT 合计: 字符串 %d, 含? %d (%.1f%%)' % (total, q, 100 * q / max(total, 1)))
