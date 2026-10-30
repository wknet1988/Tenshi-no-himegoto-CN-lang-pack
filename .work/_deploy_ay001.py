#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 draft/AY001.json：转格式(剔除敏感行) -> 重解包 -> to_jp -> build -> 部署 cn/ -> 校验。"""
import os, sys, shutil, json, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

# ---- 0) 备份当前可用 cn/ ----
bk = os.path.join('.work', 'cn_backup_before_ay001')
os.makedirs(bk, exist_ok=True)
for f in ('lcsebody', 'lcsebody.lst'):
    if os.path.exists(os.path.join('cn', f)):
        shutil.copy(os.path.join('cn', f), os.path.join(bk, f))
print('已备份当前 cn/ ->', bk)

# ---- 1) draft -> zh/AY001.json（扁平，剔除敏感行） ----
from pipeline import SENSITIVE
d = json.load(open('.work/draft/AY001.json', encoding='utf-8'))
out, dropped = {}, []
for k, v in d.items():
    if not isinstance(v, dict):
        continue
    dr = v.get('draft')
    if not isinstance(dr, str) or not dr.strip():
        continue
    if not any('\u4e00' <= c <= '\u9fff' for c in dr):
        continue
    src = v.get('src', '') or ''
    if any(w in src or w in dr for w in SENSITIVE):
        dropped.append(k)
        continue
    out[k] = dr
json.dump(out, open('.work/zh/AY001.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('AY001 译文写入 %d 条；剔除敏感 %d 条: %s' % (len(out), len(dropped), dropped))

# ---- 2) 重解包 tenshi 原版 -> .work/extract（干净日文底稿） ----
from lcse_tool import extract
n = extract('tenshi', os.path.join('.work', 'extract'))
print('重解包脚本数:', n)

# ---- 3) to_jp --apply ----
spec = importlib.util.spec_from_file_location('to_jp', os.path.join(HERE, 'tools', 'to_jp.py'))
to_jp = importlib.util.module_from_spec(spec); spec.loader.exec_module(to_jp)
to_jp.apply()

# ---- 4) inject + repack -> .work/build ----
spec2 = importlib.util.spec_from_file_location('build_zh', os.path.join(HERE, 'tools', 'build_zh.py'))
bz = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(bz)
bz.inject(); bz.repack_all()

# ---- 5) 部署 cn/ ----
shutil.copy('.work/build/lcsebody', 'cn/lcsebody')
shutil.copy('.work/build/lcsebody.lst', 'cn/lcsebody.lst')
print('已覆盖 cn/lcsebody + cn/lcsebody.lst')

# ---- 6) 校验 ----
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
recs = parse_lst('cn/lcsebody.lst')
body = open('cn/lcsebody', 'rb').read()
print('cn lst 记录:', len(recs), '| unk:', dict(Counter(r['unk'] for r in recs)))

def check(nm, show=4):
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    if not r:
        print('  %s: 未找到记录' % nm); return
    raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else body[r['offset']:r['offset'] + r['size']]
    sc = Script(raw, encoding='cp932')
    tot = q = dot = 0
    for s in sc.strings:
        tot += 1
        if '?' in s: q += 1
        if '・' in s: dot += 1
    print('  %s: 字符串 %d | 含? %d | 含中点・ %d' % (nm, tot, q, dot))
    for i in range(min(show, tot)):
        print('     [%d] %r' % (i, sc.strings[i]))

print('== AY001 =='); check('AY001', 4)
print('== 序章抽查(应仍正常) ==')
for nm in ['OP001', 'INIT']:
    check(nm, 2)
print('\nAY001 部署完成。')
