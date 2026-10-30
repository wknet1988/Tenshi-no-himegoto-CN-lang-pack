# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

EX = ('陰茎', 'ペニス', '膣', '乳房', '乳首', '精液', '射精', '舐', '挿',
      '喘', '淫', '咥', '揉', '快感', '亀頭')

for n in sys.argv[1:]:
    o = Script(open(os.path.join('.work/extract', n), 'rb').read(), encoding='cp932')
    idx = [i for i, s in enumerate(o.strings) if KANA.search(s)]
    hits = [i for i in idx if any(k in o.strings[i] for k in EX)]
    if not hits:
        print('==', n, '(无露骨词)')
        continue
    l = hits[-1]
    print('==', n, 'close from', l + 1)
    for i in idx:
        if i > l:
            t = o.strings[i].replace('\x01', '|').replace('\x02', '').replace('\x03', '')
            print(i, t[:50])
