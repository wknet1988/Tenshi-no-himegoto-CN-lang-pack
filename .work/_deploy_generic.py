#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用部署：把 zh_backup 全部译文（含新章节）重新映射/打包/部署到 cn/ 并校验目标章。
用法: python .work/_deploy_generic.py <脚本名> <跳过行(逗号分隔, 可空)>
"""
import os, sys, shutil, json, importlib.util
from collections import Counter
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))
TARGET = sys.argv[1]
def _parse_ranges(s):
    out = set()
    for part in s.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out
SKIP = _parse_ranges(sys.argv[2]) if len(sys.argv) > 2 else set()

# ---- 0) 备份当前 cn/ ----
bk = os.path.join('.work', 'cn_backup_before_%s' % TARGET)
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
print('已还原 %d 个原始简体译文' % len(names))

# ---- 2) 重解包原版日文底稿 ----
from lcse_tool import extract
n = extract('tenshi', os.path.join('.work', 'extract'))
print('重解包脚本数:', len(n) if isinstance(n, list) else n)

# ---- 3) to_jp 映射（单次） ----
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

def seg(rs, bd, nm):
    r = next((r for r in rs if r['name'].rstrip('\\').lower().endswith(nm.lower())), None)
    if not r:
        return None
    raw = x(bd[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else bd[r['offset']:r['offset'] + r['size']]
    return Script(raw, encoding='cp932')

CJK = lambda s: any('\u4e00' <= c <= '\u9fff' for c in s)
cn = seg(recs, body, TARGET)
jp = seg(orecs, obody, TARGET)
tr = json.load(open(os.path.join('.work', 'zh_backup', TARGET + '.json'), encoding='utf-8'))
inj = sum(1 for k in tr if (lambda i: (i >= len(jp.strings) or cn.strings[i] != jp.strings[i]) and CJK(cn.strings[i]))(int(k.split('#')[1])))
print('%s: 译文 %d 条 | 注入生效(含汉字且异于原版) %d | 字符串 %d' % (TARGET, len(tr), inj, len(cn.strings)))
if SKIP:
    same = sum(1 for i in SKIP if i < len(cn.strings) and i < len(jp.strings) and cn.strings[i] == jp.strings[i])
    print('跳过行与原版一致: %d/%d' % (same, len(SKIP)))
    for i in sorted(SKIP)[:4]:
        print('   #%d %s' % (i, cn.strings[i][:40]))

allt = []
for r in recs:
    if r['unk'] == 1:
        sc = seg(recs, body, r['name'])
        if sc:
            allt.extend(sc.strings)
print('全包: 含?字符串 %d | 中点(未译脚本合法katakana含在内) %d | lst %d | unk %s'
      % (sum('?' in s for s in allt), ''.join(allt).count('\u30fb'), len(recs),
         dict(Counter(r['unk'] for r in recs))))
for nm in ['OP001', 'INIT']:
    sc = seg(recs, body, nm)
    print('%s: 含汉字 %d | 含? %d' % (nm, sum(CJK(s) for s in sc.strings), sum('?' in s for s in sc.strings)))
print()
print('=== %s 抽样 ===' % TARGET)
ks = sorted(int(k.split('#')[1]) for k in tr)
for i in ks[:3] + ks[len(ks) // 2:len(ks) // 2 + 2] + ks[-3:]:
    print('  #%d %s' % (i, cn.strings[i][:64]))
print()
print('部署完成。')
