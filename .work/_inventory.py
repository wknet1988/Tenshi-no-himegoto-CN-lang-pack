#!/usr/bin/env python3
# 盘点：哪些已翻译内容没有实装到 cn/ 数据包
import json, os, sys, glob
HERE = os.getcwd()
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import parse_lst, x
from lcse_script import Script

EXTRACT = os.path.join(HERE, '.work', 'extract')
ZH      = os.path.join(HERE, '.work', 'zh')
INBOX   = os.path.join(HERE, '.work', 'inbox')
CN_DIR  = os.path.join(HERE, 'cn')

CJK = set(range(0x4e00, 0x9fff + 1))
def has_cjk(s):
    return any(ord(c) in CJK for c in (s or ''))

# ---- 原版脚本缓存 ----
sc_cache = {}
def orig_string(name, idx):
    if name not in sc_cache:
        p = os.path.join(EXTRACT, name)
        if not os.path.exists(p):
            sc_cache[name] = None
        else:
            try:
                b = x(open(p, 'rb').read(), 2)
                sc_cache[name] = Script(b, encoding='cp932')
            except Exception:
                sc_cache[name] = None
    sc = sc_cache[name]
    if sc is None:
        return None
    try:
        return sc.strings[idx]
    except Exception:
        return None

# ---- cn 数据包 ----
cn_recs = parse_lst(os.path.join(CN_DIR, 'lcsebody.lst'))
cn_body = open(os.path.join(CN_DIR, 'lcsebody'), 'rb').read()
cn_map = {r['name']: r for r in cn_recs}
cn_sc_cache = {}
def cn_script(name):
    if name not in cn_sc_cache:
        r = cn_map.get(name)
        if not r:
            cn_sc_cache[name] = None
        else:
            try:
                b = x(cn_body[r['offset']:r['offset'] + r['size']], 2)
                cn_sc_cache[name] = Script(b, encoding='cp932')
            except Exception:
                cn_sc_cache[name] = None
    return cn_sc_cache[name]

def prefix(name):
    s = name
    i = 0
    while i < len(s) and not s[i].isdigit():
        i += 1
    return s[:i] if i else name

# ---- 分析 inbox 译文（判定真翻译 + 部署率） ----
def analyze_inbox(path):
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        return None
    if not isinstance(data, dict):
        return None
    name = os.path.basename(path)[:-5]
    total = translated = differs = 0
    inj = 0  # 已注入 cn 的条数
    for k, v in data.items():
        if '#' not in k:
            continue
        nm, idxs = k.split('#', 1)
        try:
            idx = int(idxs)
        except Exception:
            continue
        if not isinstance(v, str) or not v.strip():
            continue
        total += 1
        if has_cjk(v):
            translated += 1
            o = orig_string(nm, idx)
            if o is not None and o != v:
                differs += 1
            # 部署核对
            sc = cn_script(nm)
            if sc is not None and 0 <= idx < len(sc.strings) and sc.strings[idx] == v:
                inj += 1
    return dict(name=name, total=total, cjk=translated, differs=differs, injected=inj)

# ---- 分析 draft/AY001.json（{key:{src,draft}}） ----
def analyze_draft(path):
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    name = os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path)[:-5]
    total = tr = inj = 0
    for k, v in data.items():
        if '#' not in k or not isinstance(v, dict):
            continue
        nm, idxs = k.split('#', 1)
        try:
            idx = int(idxs)
        except Exception:
            continue
        d = v.get('draft')
        if not isinstance(d, str) or not d.strip():
            continue
        total += 1
        if has_cjk(d):
            tr += 1
            sc = cn_script(nm)
            if sc is not None and 0 <= idx < len(sc.strings) and sc.strings[idx] == d:
                inj += 1
    return dict(name=name, total=total, cjk=tr, differs=tr, injected=inj)

# ---- 已部署集合（zh 顶层） ----
deployed_names = set()
for p in glob.glob(os.path.join(ZH, '*.json')):
    deployed_names.add(os.path.basename(p)[:-5])

rows = []
for p in sorted(glob.glob(os.path.join(INBOX, '*.json'))):
    r = analyze_inbox(p)
    if r:
        rows.append(r)
r = analyze_draft(os.path.join(HERE, '.work', 'draft', 'AY001.json'))
if r:
    rows.append(r)

# mt_cache 统计（哈希键，仅计数含汉字者）
try:
    mt = json.load(open(os.path.join(HERE, '.work', 'mt_cache.json'), encoding='utf-8'))
    mt_cn = sum(1 for v in mt.values() if isinstance(v, str) and has_cjk(v))
except Exception:
    mt, mt_cn = {}, 0

# sheets 是否含译文字段
try:
    sh = json.load(open(os.path.join(HERE, '.work', 'sheets', 'all.json'), encoding='utf-8'))
    sh_keys = set()
    for it in sh[:5]:
        sh_keys.update(it.keys())
    sh_has_zh = any(k in ('zh', 'dst', 'cn', 'translation', 'tr') for k in sh_keys)
except Exception:
    sh, sh_has_zh = [], False

# ---- 输出 ----
print('=' * 78)
print('已部署脚本（在 cn/ 中）:', sorted(deployed_names))
print('=' * 78)
print('%-12s %5s %5s %5s %6s  %s' % ('SCRIPT', '条目', '含汉字', '异于原版', '已注入', '状态'))
print('-' * 78)

by_series = {}
for r in rows:
    nm = r['name']
    if nm in deployed_names:
        status = '已部署'
    elif r['differs'] == 0:
        status = '原文(未译)'
    elif r['injected'] > 0:
        status = '部分注入'
    else:
        status = '未实装'
    print('%-12s %5d %5d %5d %6d  %s' % (nm, r['total'], r['cjk'], r['differs'], r['injected'], status))
    by_series.setdefault(prefix(nm), []).append((nm, r, status))

print('-' * 78)
print('mt_cache.json: %d 条，其中 %d 条含汉字(中文机翻，哈希键难直接映射)' % (len(mt), mt_cn))
print('sheets/all.json: %d 项，字段=%s，含译文字段=%s' % (len(sh), sorted(sh_keys), sh_has_zh))
print()
print('=' * 78)
print('按系列汇总（未实装 = 真翻译且未注入 cn）')
print('=' * 78)
tot_undeployed = 0
for s in sorted(by_series):
    items = by_series[s]
    un = sum(1 for _, r, st in items if st in ('未实装', '部分注入'))
    lines = sum(r['differs'] for _, r, _ in items)
    tot_undeployed += lines
    names = ','.join(nm for nm, _, _ in items)
    print('%-6s 脚本数=%2d  真译文条目=%4d  未/部分实装脚本=%d' % (s, len(items), lines, un))
    print('        ', names)
print('-' * 78)
print('未实装真译文条目合计 ≈ %d' % tot_undeployed)
