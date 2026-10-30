#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 .work/glyph_map.json。

策略（按用户要求）：
  1. 优先繁体中文字形
  2. 其次日文新/旧字体
  3. 两者都不可编码时，才沿用旧表里人工斟酌过的替代（多为近义替换）
废弃原先基于「字形部件相似」的兜底（那正是「这→迄」的成因）。

候选项之间的取舍：优先能被严格 JIS X 0208 编码的（shift_jis 可编码＝标准区，
MS 字体必定有字形）；只用 cp932 厂商扩展区编码的排在后面。
"""
import json, os, sys

ROOT = os.environ.get('GLYPH_ROOT', os.path.abspath('.'))
ZH_BACKUP = os.path.join(ROOT, '.work', 'zh_backup')
MAP = os.path.join(ROOT, '.work', 'glyph_map.json')

from opencc import OpenCC
cc_s2t = OpenCC('s2t')
try:
    cc_t2jp = OpenCC('t2jp')       # 旧字体 -> 日文新字体
except Exception:
    cc_t2jp = None
import zhconv


def cp932(ch):
    try:
        return len(ch.encode('cp932')) == 2
    except Exception:
        return False


def jis(ch):
    """严格 JIS X 0208 标准区（Python shift_jis 不含 MS 扩展区）。"""
    try:
        return len(ch.encode('shift_jis')) == 2
    except Exception:
        return False


def candidates(ch):
    """返回候选字形列表，按偏好顺序。"""
    out = []

    def add(x):
        if isinstance(x, str) and len(x) == 1 and x != ch and x not in out:
            out.append(x)

    for fn in (lambda: cc_s2t.convert(ch),
               lambda: zhconv.convert(ch, 'zh-hant'),
               lambda: cc_t2jp.convert(cc_s2t.convert(ch)) if cc_t2jp else None):
        try:
            add(fn())
        except Exception:
            pass
    return out


def pick(ch):
    """为一个 cp932 不可编码的字符挑字形。返回 (字形, 来源说明)。"""
    best = None
    for rank, c in enumerate(candidates(ch)):
        if not cp932(c):
            continue
        key = (0 if jis(c) else 1, rank)
        if best is None or key < best[0]:
            best = (key, c)
    if best is None:
        return None, 'none'
    return best[1], ('jis' if best[0][0] == 0 else 'ext')


# ---- 旧表（作为最后兜底） ----
old = json.load(open(MAP, encoding='utf-8'))
old = {k: v for k, v in old.items() if len(k) == 1 and cp932(v)}

# ---- 需要覆盖的字集：备份原始译文 + 通用简化字全域扫描（面向未来 AY001 重译） ----
inv = set()
for f in sorted(os.listdir(ZH_BACKUP)):
    if f.endswith('.json'):
        for v in json.load(open(os.path.join(ZH_BACKUP, f), encoding='utf-8')).values():
            for c in v:
                if '\u4e00' <= c <= '\u9fff' and not cp932(c):
                    inv.add(c)
corpus = set(inv)
# 全域扫描：所有「自身 cp932 不可编码 + OpenCC 认为它有繁体形态」的 CJK 基本区字
for cp in range(0x4e00, 0xa000):
    s = chr(cp)
    if cp932(s):
        continue
    try:
        if cc_s2t.convert(s) != s:
            inv.add(s)
    except Exception:
        pass

new, upgraded, kept, unresolved = {}, [], [], []
for ch in sorted(inv):
    glyph, kind = pick(ch)
    if glyph is None:
        if ch in old:
            new[ch] = old[ch]
            kept.append(ch)
        else:
            unresolved.append(ch)
        continue
    if ch in old and old[ch] != glyph:
        upgraded.append((ch, old[ch], glyph))
    new[ch] = glyph

# 旧表里存在、但全域扫描没覆盖到的条目，保留
extra_now = len(inv)
for k, v in old.items():
    new.setdefault(k, v)

print('覆盖字集: 备份语料 %d + 全域简化字扫描 -> 共 %d 需映射字' % (len(corpus), extra_now))
print('成功产出字形: %d' % sum(1 for k in new if k in inv and new[k]))
print('沿用旧表人工替代: %d' % len(kept))
print('仍无解(待近义替换): %d' % len(unresolved))
if unresolved:
    for i in range(0, len(unresolved), 40):
        print('  ' + ''.join(unresolved[i:i + 40]))
print()
print('=== 修正：由「形近/近义」升级为「繁体或日文字形」的条目 %d 个 ===' % len(upgraded))
for ch, o, n in upgraded[:80]:
    print('  %s: %s -> %s' % (ch, o, n))
if len(upgraded) > 80:
    print('  ...(共 %d)' % len(upgraded))

json.dump(new, open(MAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('已写入', MAP, '条目数', len(new))
print('关键校验: 这 ->', repr(new.get('这')), '| 惫 ->', repr(new.get('惫')), '| 碰 ->', repr(new.get('碰')))
