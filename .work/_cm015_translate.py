# -*- coding: utf-8 -*-
"""CM015（共通线第15章）译稿组装。
本章几乎全为性戏：摩菜线 #18-#87、绫线 #100-#191。
按内容边界只译框架：石阶上的思考、选择枝标签、鞋柜等待、校门等待。
"""
import json, os, sys
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

ZH_DIR = os.path.join('.work', 'zh')

T = {
 0: '场景　　１５　',
 3: '　正好在校舍和校园的中间。我坐在通往外来访客接待处的石阶上，思考着。',
 7: '先和摩菜约好',
 8: '先和绫约好',
 10: '　我回到校舍里，决定在鞋柜前等。我知道她和月岬的鞋柜不在一处。',
 15: '　今晚，我会在房间里等着。',
 91: '　在人前的地方不方便。我决定在校门等着，开始慢慢移动。',
}

SKIP = {4, 5, 11} | set(range(18, 88)) | set(range(92, 98)) | set(range(100, 192))


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'CM015'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    for i in work:
        if i in T:
            out['CM015#%d' % i] = T[i]
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing[:20])
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'CM015.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    skipped = [i for i in work if i in SKIP]
    print('目标条数: %d | 已写出: %d | 跳过: %d 条' %
          (len(work) - len(skipped), len(out), len(skipped)))
    from to_jp import drawable, MERGED
    sus = {}
    for v in out.values():
        for ch in v:
            if '一' <= ch <= '鿿' and not drawable(ch):
                sus[ch] = sus.get(ch, 0) + 1
    bad = [(c, MERGED.get(c)) for c in sorted(sus) if not MERGED.get(c)]
    print('需映射字: %d；无解: %s' % (len(sus), bad or '无'))


if __name__ == '__main__':
    main()
