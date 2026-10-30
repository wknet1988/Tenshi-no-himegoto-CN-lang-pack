#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建阶段：注入译文 + 重新打包 + 部署到 cn/ + 验证。"""
import os, sys, shutil, json, re, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

spec = importlib.util.spec_from_file_location('build_zh', os.path.join(HERE, 'tools', 'build_zh.py'))
bz = importlib.util.module_from_spec(spec); spec.loader.exec_module(bz)

print('== inject 译文 + 字体处理 ==')
bz.inject()
print('== repack 打包 -> .work/build ==')
bz.repack_all()

print('== 部署到 cn/ ==')
shutil.copy('.work/build/lcsebody', 'cn/lcsebody')
shutil.copy('.work/build/lcsebody.lst', 'cn/lcsebody.lst')
print('   已覆盖 cn/lcsebody + cn/lcsebody.lst')

print('== 验证 ==')
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
recs = parse_lst('cn/lcsebody.lst')
print('   cn lst 记录数:', len(recs))
print('   unk 分布:', dict(Counter(r['unk'] for r in recs)))
body = open('cn/lcsebody', 'rb').read()
print('   数据包大小:', len(body))

hits = tests = skipped = 0
ZH = '.work/zh'
for zp in sorted(os.listdir(ZH)):
    if not zp.endswith('.json'):
        continue
    try:
        data = json.load(open(os.path.join(ZH, zp), encoding='utf-8'))
    except Exception:
        continue
    samps = []
    for v in data.values():
        clean = ''.join(c for c in v if ord(c) >= 0x20 and c not in '\x01\x02\x03\x04')
        samps += re.findall(r'[一-鿿]{3,}', clean)[:2]
    for s in samps[:3]:
        try:
            enc = s.encode('cp932')
        except UnicodeEncodeError:
            skipped += 1; continue
        tests += 1
        if bytes(b ^ XOR_SCRIPT for b in enc) in body:
            hits += 1
print('   中文回检: %d/%d 片段命中数据包 (跳过不可编码 %d)' % (hits, tests, skipped))

# 日文残留对比
for label, s in [('です(日文残留)', 'です'), ('秘事(标题)', '秘事'), ('天使', '天使')]:
    enc = s.encode('cp932')
    n = body.count(bytes(b ^ XOR_SCRIPT for b in enc))
    print('   %-16s 命中(加密态): %d' % (label, n))

# 抽样解码 OP001 前 8 句
r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith('op001')), None)
if r:
    blob = body[r['offset']:r['offset'] + r['size']]
    raw = x(blob, XOR_SCRIPT) if r['unk'] == 1 else blob
    sc = Script(raw, encoding='cp932')
    print('   OP001 前 8 句:')
    for s in sc.strings[:8]:
        print('     ', repr(s))
print('\n构建+部署完成。')
