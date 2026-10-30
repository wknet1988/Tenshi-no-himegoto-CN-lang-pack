#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端验证当前汉化版本的数据包是否为正确的中文 cp932 构建。"""
import sys, os, json, re, hashlib
HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script

CN = os.path.join(HERE, 'cn')
LST = os.path.join(CN, 'lcsebody.lst')
BODY = os.path.join(CN, 'lcsebody')
BUILD_BODY = os.path.join(HERE, '.work', 'build', 'lcsebody')
ZH = os.path.join(HERE, '.work', 'zh')

recs = parse_lst(LST)
body = open(BODY, 'rb').read()
print('lst 记录数:', len(recs))
print('数据包大小:', len(body), '字节')

# lst 诊断：unk 取值分布 + 前 3 条原始记录
from collections import Counter
print('unk 分布:', dict(Counter(r['unk'] for r in recs)))
for r in recs[:3]:
    print('  样本记录:', r)

def is_script(r):
    return r['unk'] == 1 or r['name'].lower().endswith('.lcs')
scripts = [r for r in recs if is_script(r)]
print('脚本记录(unk==1 或 .lcs):', len(scripts))

# 1) 反向检索：译文 JSON 里的真实中文，cp932 编码后 XOR 0x02，应在数据包中出现
tests = hits = 0
skipped = 0
for zp in sorted(os.listdir(ZH)):
    if not zp.endswith('.json'):
        continue
    try:
        data = json.load(open(os.path.join(ZH, zp), encoding='utf-8'))
    except Exception as e:
        print('  [跳过损坏 json]', zp, e)
        continue
    samps = []
    for v in data.values():
        clean = ''.join(c for c in v if ord(c) >= 0x20 and c not in '\x01\x02\x03\x04')
        samps += re.findall(r'[一-鿿]{3,}', clean)[:2]
    for s in samps[:3]:
        try:
            enc = s.encode('cp932')
        except UnicodeEncodeError:
            skipped += 1
            continue
        probes = bytes(b ^ XOR_SCRIPT for b in enc)
        tests += 1
        if probes in body:
            hits += 1
print('中文回检: %d/%d 片段命中数据包 (utf8->cp932->XOR 落在 cn/lcsebody)' % (hits, tests),
      '| cp932 不可编码而跳过:', skipped)

# 2) 抽样解码 OP001 / INIT 脚本的前若干字符串，肉眼确认是中文
for tgt in ('OP001', 'INIT'):
    r = next((r for r in recs if r['name'].rstrip('\\').lower().endswith(tgt.lower())
              or r['name'].rstrip('\\').lower().endswith(tgt.lower() + '.lcs')), None)
    if not r:
        print('未找到记录:', tgt)
        continue
    blob = body[r['offset']:r['offset'] + r['size']]
    raw = x(blob, XOR_SCRIPT) if r['unk'] == 1 else blob
    sc = Script(raw, encoding='cp932')
    print('\n=== %s 解码前 12 条字符串 ===' % tgt)
    for s in sc.strings[:12]:
        print(repr(s))

# 3) cn/lcsebody 与最新 build/lcsebody 是否一致
if os.path.exists(BUILD_BODY):
    h1 = hashlib.md5(body).hexdigest()
    h2 = hashlib.md5(open(BUILD_BODY, 'rb').read()).hexdigest()
    print('\ncn/lcsebody  md5:', h1)
    print('build/lcsebody md5:', h2)
    print('两者一致:', h1 == h2)
else:
    print('build/lcsebody 不存在，跳过比对')
