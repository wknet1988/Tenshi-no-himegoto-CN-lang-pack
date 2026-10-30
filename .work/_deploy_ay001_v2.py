#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 AY001 人工重译（155 条非情色译文）到 cn/。
链路：备份 cn/ -> 从 zh_backup 还原原始简体(含新 AY001) -> 重解包 -> to_jp --apply
      -> build_zh(inject+repack) -> 部署 -> 校验。
边界：#16/#35/#36/#280-501/#503/#505/#509/#510/#516/#518/#33 等保留日文。
"""
import os, sys, shutil, json, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))

# ---- 0) 备份当前 cn/ ----
bk = os.path.join('.work', 'cn_backup_before_ay001_v2')
os.makedirs(bk, exist_ok=True)
for f in ('lcsebody', 'lcsebody.lst'):
    shutil.copy(os.path.join('cn', f), os.path.join(bk, f))
print('已备份当前 cn/ ->', bk)

# ---- 1) 还原原始简体译文（含新 AY001） ----
ZHB = os.path.join('.work', 'zh_backup')
ZHD = os.path.join('.work', 'zh')
names = [f for f in sorted(os.listdir(ZHB)) if f.endswith('.json')]
for f in names:
    shutil.copy(os.path.join(ZHB, f), os.path.join(ZHD, f))
print('已还原 %d 个原始简体译文（含 AY001）: %s' % (len(names), names))

# ---- 2) 重解包原版日文底稿 ----
from lcse_tool import extract
n = extract('tenshi', os.path.join('.work', 'extract'))
print('重解包脚本数:', len(n) if isinstance(n, list) else n)

# ---- 3) to_jp 映射（单次，从原始简体） ----
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
print('映射后：字符串 %d | 中点・ %d | 问号 %d' % (tot_s, tot_dot, tot_q))

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
orecs = parse_lst('tenshi/lcsebody.lst')
obody = open('tenshi/lcsebody', 'rb').read()
print()
print('cn lst 记录:', len(recs), '| unk:', dict(Counter(r['unk'] for r in recs)))

def seg(recs, body, nm):
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    if not r:
        return None
    raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else body[r['offset']:r['offset'] + r['size']]
    return Script(raw, encoding='cp932')

CJK = lambda s: any('\u4e00' <= c <= '\u9fff' for c in s)

cn_ay = seg(recs, body, 'AY001')
jp_ay = seg(orecs, obody, 'AY001')
injected = sum(1 for i, s in enumerate(cn_ay.strings)
               if (i >= len(jp_ay.strings) or s != jp_ay.strings[i]) and CJK(s))
print('AY001 字符串 %d | 注入译文(异于原版且含汉字) %d（应=155）' % (len(cn_ay.strings), injected))

# 跳过行必须与原版字节一致（453/454 选择枝标签已译，除外）
SKIP = [16, 35, 36, 33, 306, 387, 433, 503, 505, 509, 510, 516, 518] + [i for i in range(280, 502) if i not in (453, 454)]
same = sum(1 for i in SKIP if i < len(cn_ay.strings) and i < len(jp_ay.strings) and cn_ay.strings[i] == jp_ay.strings[i])
print('跳过行与原版一致: %d/%d' % (same, len([i for i in SKIP if i < len(cn_ay.strings)])))

# 全包 ? / 中点
allt = []
for r in recs:
    if r['unk'] != 1:
        continue
    sc = seg(recs, body, r['name'])
    if sc:
        allt.extend(sc.strings)
t = ''.join(allt)
print('全包含?字符串: %d | 中点・: %d | 问号字符: %d' % (sum('?' in s for s in allt), t.count('\u30fb'), t.count('?')))

# 序章完好性
for nm in ['OP001', 'INIT']:
    sc = seg(recs, body, nm)
    cjk = sum(CJK(s) for s in sc.strings)
    print('%s: 字符串 %d | 含汉字 %d | 含? %d' % (nm, len(sc.strings), cjk, sum('?' in s for s in sc.strings)))

print()
print('=== AY001 译文抽样 ===')
for i in [0, 7, 13, 30, 68, 96, 141, 168, 237, 273, 523, 535, 557, 562]:
    if i < len(cn_ay.strings):
        print('  #%d %s' % (i, cn_ay.strings[i][:64]))
print()
print('=== 跳过行抽样（应仍为日文）===')
for i in [16, 35, 280, 300, 453, 454, 501, 505, 509]:
    if i < len(cn_ay.strings):
        print('  #%d %s' % (i, cn_ay.strings[i][:44]))
print()
print('部署完成。')
