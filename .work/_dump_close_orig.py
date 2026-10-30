# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'tools')
from lcse_tool import parse_lst, x, XOR_SCRIPT
from lcse_script import Script
from pipeline import KANA
R = parse_lst('tenshi/lcsebody.lst')
B = open('tenshi/lcsebody', 'rb').read()
EX = ('陰茎', '膣', '乳房', '乳首', '精液', '射精', '舐', '挿', '喘', '淫', '咥', '揉', '亀頭')


def load(n):
    r = [r for r in R if r['name'].rstrip('\\').lower().endswith(n.lower())][0]
    raw = x(B[r['offset']:r['offset'] + r['size']], XOR_SCRIPT) if r['unk'] == 1 else B[r['offset']:r['offset'] + r['size']]
    return Script(raw, encoding='cp932')


for n in sys.argv[1:]:
    o = load(n)
    idx = [i for i, s in enumerate(o.strings) if KANA.search(s)]
    hits = [i for i in idx if any(k in o.strings[i] for k in EX)]
    if not hits:
        print('==', n, 'no-hit')
        continue
    last = hits[-1]
    print('==', n, 'from', last + 1)
    for i in idx:
        if i > last:
            t = o.strings[i].replace('\x01', '|').replace('\x02', '').replace('\x03', '')
            print(i, t)
