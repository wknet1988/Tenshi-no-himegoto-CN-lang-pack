#!/usr/bin/env python3
# 修正版盘点：以 cn/lcsebody（实装包）为基准，判定 inbox/draft 是否"真译文且未实装"
import json, os, sys, glob
HERE = os.getcwd()
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import parse_lst, x
from lcse_script import Script

CN_DIR = os.path.join(HERE, 'cn')
INBOX  = os.path.join(HERE, '.work', 'inbox')
ZH     = os.path.join(HERE, '.work', 'zh')

CJK = set(range(0x4e00, 0x9fff + 1))
def has_cjk(s): return any(ord(c) in CJK for c in (s or ''))

# cn 数据包
cn_recs = parse_lst(os.path.join(CN_DIR, 'lcsebody.lst'))
cn_body = open(os.path.join(CN_DIR, 'lcsebody'), 'rb').read()
cn_map = {r['name']: r for r in cn_recs}
cn_sc = {}
def cn_string(name, idx):
    if name not in cn_sc:
        r = cn_map.get(name)
        if not r:
            cn_sc[name] = None
        else:
            try:
                b = x(cn_body[r['offset']:r['offset'] + r['size']], 2)
                cn_sc[name] = Script(b, encoding='cp932')
            except Exception:
                cn_sc[name] = None
    sc = cn_sc[name]
    if sc is None or not (0 <= idx < len(sc.strings)):
        return None
    return sc.strings[idx]

deployed = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ZH, '*.json'))}

def analyze(path, keyfmt='NAME#IDX', field=None):
    data = json.load(open(path, encoding='utf-8'))
    if not isinstance(data, dict):
        return None
    name = os.path.basename(path)[:-5]
    tot = cjk = untrans = undep = 0   # undep = 真译文且未实装
    for k, v in data.items():
        if '#' not in k:
            continue
        nm, idxs = k.split('#', 1)
        try: idx = int(idxs)
        except: continue
        if field:                       # draft 结构 {key:{src,draft}}
            if not isinstance(v, dict): continue
            v = v.get(field)
        if not isinstance(v, str) or not v.strip():
            continue
        tot += 1
        if not has_cjk(v):
            continue
        cjk += 1
        c = cn_string(nm, idx)
        if c is None:
            untrans += 1               # cn 无此脚本/下标（异常）
            continue
        if v == c:
            untrans += 1               # inbox==cn：未译原文 或 已实装
        else:
            undep += 1                 # inbox 与 cn 不同且含汉字：真译文未实装
    return dict(name=name, tot=tot, cjk=cjk, undep=undep, same_as_cn=cjk-undep)

rows = []
for p in sorted(glob.glob(os.path.join(INBOX, '*.json'))):
    r = analyze(p)
    if r: rows.append(r)
r = analyze(os.path.join(HERE, '.work', 'draft', 'AY001.json'), field='draft')
if r: rows.append(r)

# mt_cache 哈希键，仅统计中文条数
mt = json.load(open(os.path.join(HERE, '.work', 'mt_cache.json'), encoding='utf-8'))
mt_cn = sum(1 for v in mt.values() if isinstance(v, str) and has_cjk(v))

def prefix(n):
    i = 0
    while i < len(n) and not n[i].isdigit(): i += 1
    return n[:i] if i else n

# 样本核验
print('=== 样本核验（inbox vs cn 实装包）===')
for nm in ['AY001', 'AY010', 'H018', 'CM002']:
    ib = json.load(open(os.path.join(INBOX, nm + '.json'), encoding='utf-8'))
    for idx in [0, 5, 10]:
        kv = ib.get(f'{nm}#{idx}')
        cv = cn_string(nm, idx)
        kvr = (kv[:30] if isinstance(kv, str) else kv)
        cvr = (cv[:30] if isinstance(cv, str) else cv)
        print(f'{nm}#{idx}: inbox={kvr!r} | cn={cvr!r} | 相同={kv==cv}')

print()
print('=' * 78)
print('已实装脚本（cn/ 中，来自 zh/ 顶层）:', sorted(deployed))
print('=' * 78)
print('%-12s %5s %5s %7s %9s  %s' % ('SCRIPT', '可译条', '含汉字', '真译文未装', '同cn(未译)', '状态'))
print('-' * 78)
by_s = {}
for r in rows:
    st = '已实装' if r['name'] in deployed else ('未实装' if r['undep'] > 0 else '原文未译')
    print('%-12s %5d %5d %7d %9d  %s' % (r['name'], r['tot'], r['cjk'], r['undep'], r['same_as_cn'], st))
    by_s.setdefault(prefix(r['name']), []).append((r, st))

print('-' * 78)
print('mt_cache.json: %d 条，%d 条含汉字(中文机翻，哈希键难映射回脚本)' % (len(mt), mt_cn))
print('=' * 78)
print('按系列汇总（真译文未实装 = 与 cn 不同且含汉字）')
print('=' * 78)
tot = 0
for s in sorted(by_s):
    items = by_s[s]
    un = sum(r['undep'] for r, _ in items)
    tot += un
    names = ','.join(nm for (r, _), nm in [(x, x[0]['name']) for x in items])
    print('%-6s 脚本=%2d  真译文未实装条目=%4d' % (s, len(items), un))
    print('        ', names)
print('-' * 78)
print('★ 真译文未实装条目合计 ≈ %d' % tot)
