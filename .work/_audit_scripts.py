#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐章审计：定位含未成年角色性描写的区间（SENSITIVE 词表抓不住软色情，须人工级检测）。

方法：
  1. 强特征词表（露骨性用语）+ 喘息台词检测（假名密度+終助詞模式）
  2. 说话人跟踪（绫/摩菜/女生徒=儿童角色；イリーナ/沙織/英之=成人）
  3. 连续块检测（间隔<=4 行视为同一场戏）
输出只含计数/下标/说话人，不引用任何台词原文。
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.abspath('.'), 'tools'))
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
from pipeline import KANA

STRONG = [
 '射精','愛液','精液','体液','処女','貞操','淫','痴','凌辱','強姦','輪姦','挿入','抽送',
 'ピストン','膣','子宮','乳首','乳頭','勃起','陰茎','怒張','疼','滾','濡','蜜','汁','シミ',
 '打ち付け','突き上げ','喘','嬌声','嗚咽','痙攣','仰け反','仰向け','跨がり','跨り','跪',
 '這いつくば','四つん','馬乗り','素股','擦り','擦っ','こすり','押し付け','押し当て','埋め',
 '抉じ','抉り','抉っ','割れ','裂け','入口','最奥','奥深','雁','広げ','はだけ','脱が','剥き',
 'たくし','まくり','露わ','露に','全裸','半裸','一糸','まとわ','ふんどし','咥え','しゃぶ',
 '舐め','舐り','舐っ','吸っ','吸い','甘噛','噛み','唾液','接吻','キス','唇','内腿','太もも',
 '太腿','尻','臀部','胸元','乳房','素肌','肌が','火照り','火照っ','硬く','硬い','膨ら',
 'ビク','わなわな','食い締','絞り','果て','イク','イッ','絶頂','達し','シたい','むらむら',
 'たまらない','抑え','こらえ','獣','支配','従順','悶え','乱れ','乱暴','狂い','痴女','痴男',
]
MOAN_VOW = set('あんはぁふくちゅぴゅゆろれわなもおえ')
MOAN_TAIL = ['だめ','いや','やん','嬉しく','苦しい','気持ち','せつない','切ない','だめぇ','らめぇ','ひど','もっと','すご','お兄','だって','ふぅ','んん','はぁ','ああ','あん']

def speaker(s):
    return s.split('\x01')[0] if '\x01' in s else ''

MINORS = {'綾','摩菜','女生徒','女子生徒','子供','少女','幼い'}
ADULTS = {'イリーナ','沙織','英之','委員長','礼美','先生'}

def is_moan(s):
    """喘息台词：短行 + 假名元音密集 + 終助詞/終端音"""
    k = sum(1 for c in s if c in MOAN_VOW)
    if len(s) > 45 or k < 4:
        return False
    if any(t in s for t in MOAN_TAIL):
        return True
    return ('っ' in s or 'ー' in s) and k >= 6

def flag_line(s):
    hits = [w for w in STRONG if w in s]
    if is_moan(s):
        hits.append('(喘)')
    return hits

def blocks(flags, gap=4):
    """flags: {idx: hits} -> [(start,end,hits_total)]"""
    idxs = sorted(flags)
    out = []
    for i in idxs:
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [(a, b) for a, b in out]

recs = parse_lst('tenshi/lcsebody.lst')
body = open('tenshi/lcsebody', 'rb').read()
done = {'OP001','OP002','OP003','OP004','OP005A','OP005B','OP006','INIT','_LOADATTITLE','AY001'}

rows = []
detail = []
for r in recs:
    if r['unk'] != 1:
        continue
    nm = r['name'].rstrip('\\')
    if nm in done:
        continue
    raw = x(body[r['offset']:r['offset'] + r['size']], XOR_SCRIPT)
    sc = Script(raw, encoding='cp932')
    tr = [i for i, s in enumerate(sc.strings) if KANA.search(s)]
    if not tr:
        continue
    flags = {}
    spk_in = {}
    for i in tr:
        s = sc.strings[i]
        h = flag_line(s)
        if h:
            flags[i] = h
            sp = speaker(s)
            spk_in.setdefault(sp or '(旁白)', 0)
            spk_in[sp or '(旁白)'] += 1
    blks = blocks(flags)
    minor_blk = []
    for a, b in blks:
        spk = {}
        for i in range(a, b + 1):
            if i in flags:
                sp = speaker(sc.strings[i]) or '(旁白)'
                spk[sp] = spk.get(sp, 0) + 1
        minor_blk.append((a, b, b - a + 1, spk))
    rows.append((nm, len(tr), len(flags), len(blks), max((b - a + 1) for a, b, _, _ in minor_blk) if minor_blk else 0, minor_blk, spk_in))
    detail.append((nm, sc, tr, flags, minor_blk))

# ---- 汇总表 ----
print('%-10s %5s %5s %5s %6s   %s' % ('脚本', '可译', '标记', '块数', '最长块', '判定'))
for nm, ntr, nfl, nbl, mx, blks, spk in sorted(rows, key=lambda t: -t[2]):
    if nfl == 0:
        verdict = '干净'
    elif nfl / ntr >= 0.5:
        verdict = '情戏主导'
    elif nfl / ntr >= 0.15:
        verdict = '含情戏块'
    else:
        verdict = '零星'
    print('%-10s %5d %5d %5d %6d   %s' % (nm, ntr, nfl, nbl, mx, verdict))

print()
print('=== 各脚本儿童角色涉入情况（说话人含绫/摩菜/女生徒 且 有标记行）===')
for nm, ntr, nfl, nbl, mx, blks, spk in sorted(rows):
    if not blks:
        continue
    minor_spk = [s for s in spk if s in MINORS]
    allspk = sorted(spk)
    has_minor_block = any(any(s in MINORS for s in blk[3]) for blk in blks)
    tag = '★儿童参演' if has_minor_block else ('△儿童在场(说话)' if minor_spk else '')
    print('%-10s 标记%3d 块%2d 最长%3d  说话人:%s %s' % (nm, nfl, nbl, mx, ','.join(allspk[:8]), tag))

json.dump({'rows': [(nm, ntr, nfl, nbl, mx) for nm, ntr, nfl, nbl, mx, _, _ in rows]},
          open('.work/_audit_summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('汇总已存 .work/_audit_summary.json')
