#!/usr/bin/env python3
import os, json
HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ZH = os.path.join(HERE, '.work', 'zh')
ZB = os.path.join(HERE, '.work', 'zh_backup')

zh_main = {f for f in os.listdir(ZH) if f.endswith('.json')}
zb = {f for f in os.listdir(ZB) if f.endswith('.json')}
print('zh 主目录 json 数:', len(zh_main))
print('zh_backup json 数:', len(zb))
print('backup 覆盖主目录的:', sorted(zh_main & zb))
print('主目录有、backup 缺失的(潜在缺口):', sorted(zh_main - zb))

# mt_cache / 其他可能含译文的源
for cand in ['mt_cache.json', 'zh_src_cm002.json', 'glyph_map.json',
             'extra_map.json', 'near_map.json', 'more_map.json', 'ay010_missing.json']:
    p = os.path.join(HERE, '.work', cand)
    if not os.path.exists(p):
        continue
    raw = open(p, 'rb').read()
    head = raw[:60]
    # 判断是否像 {脚本#idx: 译文} 结构
    like = False
    try:
        d = json.loads(raw)
        like = any('#' in str(k) for k in list(d)[:50]) and isinstance(d, dict)
        print('  %-22s %8d B  类译文缓存=%s  样本key=%s' % (cand, len(raw), like, list(d)[:2]))
    except Exception as e:
        print('  %-22s %8d B  非json(%s) head=%s' % (cand, len(raw), e, head[:30]))
