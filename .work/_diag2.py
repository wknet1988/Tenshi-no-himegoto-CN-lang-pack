#!/usr/bin/env python3
import os, sys
HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import parse_lst

# A) zh_backup 是否含有效译文
ZB = os.path.join(HERE, '.work', 'zh_backup')
print('=== .work/zh_backup 文件 ===')
files = sorted(os.listdir(ZB)) if os.path.isdir(ZB) else []
print('数量:', len(files))
ok = bad = 0
sample = None
for f in files:
    if not f.endswith('.json'):
        continue
    p = os.path.join(ZB, f)
    sz = os.path.getsize(p)
    head = open(p, 'rb').read(20)
    if head.strip(b'\x00') == b'' :
        bad += 1
    else:
        ok += 1
        if sample is None and sz > 50:
            sample = f
print('非空 json:', ok, '| 全零 json:', bad)

if sample:
    print('\n样本译文文件:', sample)
    try:
        import json
        d = json.load(open(os.path.join(ZB, sample), encoding='utf-8'))
        print('  解析成功, 条目数:', len(d))
        k0 = next(iter(d))
        print('  首条 key=%s value=%r' % (k0, d[k0][:60]))
    except Exception as e:
        print('  仍解析失败:', e)

# B) tenshi 原版 lst 是否完好，能否作为 cn/lcsebody.lst 的模板
TL = os.path.join(HERE, 'tenshi', 'lcsebody.lst')
print('\n=== tenshi/lcsebody.lst ===')
if os.path.exists(TL):
    raw = open(TL, 'rb').read()
    print('大小:', len(raw), '| 前 16 字节 hex:', raw[:16].hex())
    try:
        recs = parse_lst(TL)
        print('解析记录数:', len(recs))
        print('unk 分布:', __import__('collections').Counter(r['unk'] for r in recs))
        print('样本:', recs[0], recs[1])
    except Exception as e:
        print('解析失败:', e)
else:
    print('不存在')

# C) cn/lcsebody.lst 全文件是否真的全零
CL = os.path.join(HERE, 'cn', 'lcsebody.lst')
data = open(CL, 'rb').read()
print('\n=== cn/lcsebody.lst 是否全零 ===')
print('大小:', len(data), '| 非零字节数:', sum(1 for b in data if b))
