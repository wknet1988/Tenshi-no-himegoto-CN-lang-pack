#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整重建：干净底稿 + to_jp 映射 + build + 部署 cn/ + 验证。"""
import os, sys, shutil, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

print('== 1) 重新解包 tenshi 原版 -> .work/extract (干净日文底稿) ==')
from lcse_tool import extract
print('   extract 文件数:', len(extract('tenshi', os.path.join('.work', 'extract'))))

print('== 2) to_jp --apply (简化字 -> cp932 可编码字形) ==')
spec_jp = importlib.util.spec_from_file_location('to_jp', os.path.join(HERE, 'tools', 'to_jp.py'))
to_jp = importlib.util.module_from_spec(spec_jp); spec_jp.loader.exec_module(to_jp)
to_jp.apply()

print('== 3) inject + repack -> .work/build ==')
spec_bz = importlib.util.spec_from_file_location('build_zh', os.path.join(HERE, 'tools', 'build_zh.py'))
bz = importlib.util.module_from_spec(spec_bz); spec_bz.loader.exec_module(bz)
bz.inject()
bz.repack_all()

print('== 4) 部署到 cn/ ==')
shutil.copy('.work/build/lcsebody', 'cn/lcsebody')
shutil.copy('.work/build/lcsebody.lst', 'cn/lcsebody.lst')
print('   已覆盖 cn/lcsebody + cn/lcsebody.lst')

print('== 5) 验证 ==')
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
recs = parse_lst('cn/lcsebody.lst')
body = open('cn/lcsebody', 'rb').read()
print('   cn lst 记录数:', len(recs), '| unk:', dict(Counter(r['unk'] for r in recs)))
q = dot = total = 0
for nm in ['OP001', 'OP002', 'OP003', 'OP004', 'OP005A', 'OP005B', 'OP006', 'INIT', '_LOADATTITLE']:
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    if not r:
        continue
    blob = body[r['offset']:r['offset'] + r['size']]
    raw = x(blob, XOR_SCRIPT) if r['unk'] == 1 else blob
    sc = Script(raw, encoding='cp932')
    for s in sc.strings:
        total += 1
        if '?' in s:
            q += 1
        if '・' in s:
            dot += 1
print('   序章+INIT 字符串 %d | 含? %d | 含中点・ %d' % (total, q, dot))

r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith('op001')), None)
raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT)
sc = Script(raw, encoding='cp932')
print('   OP001 前 6 句:')
for s in sc.strings[:6]:
    print('     ', repr(s))
print('\n完整重建完成。')
