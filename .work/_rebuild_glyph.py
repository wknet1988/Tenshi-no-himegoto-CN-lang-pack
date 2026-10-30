#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用重建后的 glyph_map 重做：还原原始简体 -> to_jp 映射 -> 打包 -> 部署 -> 校验。"""
import os, sys, shutil, json, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

# ---- 0) 备份当前 cn/ ----
bk = os.path.join('.work', 'cn_backup_before_glyphfix')
os.makedirs(bk, exist_ok=True)
for f in ('lcsebody', 'lcsebody.lst'):
    shutil.copy(os.path.join('cn', f), os.path.join(bk, f))
print('已备份当前 cn/ ->', bk)

# ---- 1) 还原原始简体译文 ----
ZHB = os.path.join('.work', 'zh_backup')
ZHD = os.path.join('.work', 'zh')
names = [f for f in sorted(os.listdir(ZHB)) if f.endswith('.json')]
for f in names:
    shutil.copy(os.path.join(ZHB, f), os.path.join(ZHD, f))
print('已还原 %d 个原始简体译文:' % len(names), names)
print('zh/ 内文件:', sorted(os.listdir(ZHD)))

# ---- 2) 重解包原版日文底稿 ----
from lcse_tool import extract
n = extract('tenshi', os.path.join('.work', 'extract'))
print('重解包脚本数:', len(n) if isinstance(n, list) else n)

# ---- 3) to_jp 映射（新表） ----
spec = importlib.util.spec_from_file_location('to_jp', os.path.join(HERE, 'tools', 'to_jp.py'))
to_jp = importlib.util.module_from_spec(spec); spec.loader.exec_module(to_jp)
to_jp.apply()

# ---- 4) 映射后就地统计 ----
tot_dot = tot_q = tot_s = 0
for f in sorted(os.listdir(ZHD)):
    if f.endswith('.json'):
        d = json.load(open(os.path.join(ZHD, f), encoding='utf-8'))
        for v in d.values():
            tot_s += 1
            tot_dot += v.count('\u30fb')
            tot_q += v.count('?')
print()
print('映射后：字符串 %d | 中点・ %d 个 | 问号 %d 个' % (tot_s, tot_dot, tot_q))

# ---- 5) 注入 + 重打包 ----
spec2 = importlib.util.spec_from_file_location('build_zh', os.path.join(HERE, 'tools', 'build_zh.py'))
bz = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(bz)
bz.inject(); bz.repack_all()

# ---- 6) 部署 ----
shutil.copy('.work/build/lcsebody', 'cn/lcsebody')
shutil.copy('.work/build/lcsebody.lst', 'cn/lcsebody.lst')
print('已部署 cn/')

# ---- 7) 校验 ----
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
recs = parse_lst('cn/lcsebody.lst')
body = open('cn/lcsebody', 'rb').read()
print('cn lst 记录:', len(recs), '| unk:', dict(Counter(r['unk'] for r in recs)))

def seg(nm):
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else body[r['offset']:r['offset'] + r['size']]
    return Script(raw, encoding='cp932')

names = [f[:-5] for f in sorted(os.listdir(ZHB)) if f.endswith('.json')]
all_dot = all_q = 0
has_zhe = False
for nm in names:
    sc = seg(nm)
    d = sum(s.count('\u30fb') for s in sc.strings)
    q = sum('?' in s for s in sc.strings)
    all_dot += d; all_q += q
    if any('這' in s for s in sc.strings):
        has_zhe = True
    print('  %-14s 字符串 %4d | 中点 %3d | 问号 %d' % (nm, len(sc.strings), d, q))
print()
print('合计：中点 %d（修复前 440） | 问号 %d | 「這」已出现: %s | 「迄」残留: %s'
      % (all_dot, all_q, has_zhe, any('迄' in s for s in seg('OP001').strings)))
print()
print('=== 效果抽样 ===')
sc = seg('OP001')
for i, s in enumerate(sc.strings[:6]):
    print('  [%d] %r' % (i, s))
print()
print('=== 成果词抽查（应为正统词） ===')
probe = ['薔薇', '蝋燭', '冗長', '窓辺', '害羞', '傷痕', '磨擦', '握住', '逃脱', '火炎']
alltext = ''.join(seg(nm).strings for nm in names)
for w in probe:
    print('  %s: %s' % (w, '在' if w in alltext else '未出现'))
print()
print('字形映射重做完成。')
