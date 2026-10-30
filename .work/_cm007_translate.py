# -*- coding: utf-8 -*-
"""CM007（共通线第7章）译稿组装。
本章整章为两段儿童角色性戏（#20-#123 摩菜线、#125-#230 绫线），按边界整段跳过；
仅译开头氛围铺垫、选择枝标签与结尾旁白。
"""
import json, os, sys
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

ZH_DIR = os.path.join('.work', 'zh')

T = {
 0: '场景　　０７　',
 4: '　夜已深，到了晚上１１点，我开始考虑差不多该把房间的灯熄了。',
 5: '　不经意地窜过…后颈一阵刺痒的独特感觉，让我不由自主地合上正读着的文库本，站了起来。',
 6: '　恰好，就在正上方…摩菜和绫两人的房间那一带。感觉到的是令人不安的…『那家伙』的气息。',
 7: '　之前抱住她们，才不过三天左右啊…。',
 8: '　不可能是错觉。尽管感觉到『那家伙』的时间连一秒都不到，可那像湿皮肤上粘了砂子般的不快感却挥之不去。',
 9: '　叹息…深呼吸一口气让心情平复下来，赶往门边。',
 10: '　已经不再犹豫。',
 11: '　因为，我给自己赋予了拯救那两人的使命。',
 13: '去看看摩菜的情况',
 14: '去看看绫的情况',
 226: '　这是如梦一般的…绝不是会给绫光辉的未来投下阴影的东西。',
 227: '　希望她能忘掉。像梦一样…。',
}

SKIP = set(range(20, 231))


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'CM007'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    skipped = []
    for i in work:
        if i in SKIP:
            skipped.append(i)
            continue
        if i in T:
            out['CM007#%d' % i] = T[i]
        else:
            print('!! 缺少译文: #%d' % i)
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing)
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'CM007.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('目标条数: %d | 已写出: %d | 跳过: %d 条(#20-#230 整段性戏)' %
          (len(work) - len(skipped), len(out), len(skipped)))
    from to_jp import drawable, MERGED
    sus = {}
    for v in out.values():
        for ch in v:
            if '一' <= ch <= '鿿' and not drawable(ch):
                sus[ch] = sus.get(ch, 0) + 1
    print('需映射字: %d；无解: %s' % (len(sus), [c for c in sus if not MERGED.get(c)] or '无'))


if __name__ == '__main__':
    main()
