#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回退 AY001 机翻：备份当前 cn/ -> 移出 zh/AY001.json -> 重解包 -> to_jp -> build -> 部署 -> 校验。"""
import os, sys, shutil, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

# ---- 0) 备份当前带机翻的 cn/（便于对照） ----
bk = os.path.join('.work', 'cn_backup_ay001_mt')
os.makedirs(bk, exist_ok=True)
for f in ('lcsebody', 'lcsebody.lst'):
    if os.path.exists(os.path.join('cn', f)):
        shutil.copy(os.path.join('cn', f), os.path.join(bk, f))
print('已备份当前(含机翻) cn/ ->', bk)

# ---- 1) 把 AY001 译文移出 zh/（保留到 _mt_reverted 备将来人工重译） ----
zh = os.path.join('.work', 'zh')
mt_dir = os.path.join('.work', 'zh', '_mt_reverted')
os.makedirs(mt_dir, exist_ok=True)
src = os.path.join(zh, 'AY001.json')
if os.path.exists(src):
    shutil.move(src, os.path.join(mt_dir, 'AY001.json'))
    print('已移出 zh/AY001.json -> zh/_mt_reverted/AY001.json')
else:
    print('zh/AY001.json 不存在，跳过')
print('zh/ 剩余译文文件:', sorted(f for f in os.listdir(zh) if f.endswith('.json')))

# ---- 2) 重解包 tenshi 原版 -> .work/extract（干净日文底稿） ----
from lcse_tool import extract
n = extract('tenshi', os.path.join('.work', 'extract'))
print('重解包脚本数:', n)

# ---- 3) to_jp --apply（日文底稿本就在 cp932 范围内，基本不变） ----
spec = importlib.util.spec_from_file_location('to_jp', os.path.join(HERE, 'tools', 'to_jp.py'))
to_jp = importlib.util.module_from_spec(spec); spec.loader.exec_module(to_jp)
to_jp.apply()

# ---- 4) inject + repack -> .work/build（不再含 AY001，故回退为日文） ----
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

print('== AY001（应为日文）=='); check('AY001', 4)
print('== 序章抽查(应仍中文) ==')
for nm in ['OP001', 'INIT']:
    check(nm, 2)
# 与原版 tenshi 比对 AY001 是否一致（回退成功标志）
orecs = parse_lst('tenshi/lcsebody.lst'); obody = open('tenshi/lcsebody','rb').read()
ro = next((r for r in orecs if r['name'].rstrip('\\').lower().endswith('ay001')), None)
rc = next((r for r in recs if r['name'].rstrip('\\').lower().endswith('ay001')), None)
o_raw = x(obody[ro['offset']:ro['offset']+ro['size']], XOR_SCRIPT) if ro['unk']==1 else obody[ro['offset']:ro['offset']+ro['size']]
c_raw = x(body[rc['offset']:rc['offset']+rc['size']], XOR_SCRIPT) if rc['unk']==1 else body[rc['offset']:rc['offset']+rc['size']]
print('AY001 与原版 tenshi 字节一致:', o_raw == c_raw)
print('\nAY001 机翻回退完成。')
