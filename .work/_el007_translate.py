# -*- coding: utf-8 -*-
"""EL007（退廃０９）译稿组装。
内容：委員長（摩菜・綾的同班同学）来访，报告羽白沙織的异状→英之在恶魔
      侵蚀中勉强应对→送走委員長→铃声→綾的口交突入（#36 起）。
边界：#22/#36/#37 为与未成年者同室相关的性暗示与实际性描写，跳过保留日文。
"""
import json, os, sys
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

ZH_DIR = os.path.join('.work', 'zh')


def wrap(orig, cur):
    if '\x01' not in orig:
        return cur
    i = orig.index('\x01')
    pre = orig[:i + 1]
    j = orig.find('\x02', i)
    suf = orig[j:] if j >= 0 else ''
    if i == 0:
        return pre + cur + suf
    body = cur[cur.index('「'):] if '「' in cur else '「' + cur + '」'
    return pre + body + suf


T = {
 0: '退廃　　　０９　',
 7: '委員長「………就是这样。最近的羽白同学，简直像是在刻意与班上的众人保持距离。她到底在想些什么呢……」',
 8: '英之「是吗……我倒是没有注意到」',
 9: '　似乎是在替摩菜和綾担心，那个戴眼镜的……记得是她们俩的同班同学，说着说着似乎激动起来，脸上泛起了红晕。',
 11: '委員長「也就是说，在家里她的举止并没有变化吗」',
 12: '　这位不速之客气势十足，朝着坐在椅子上的我步步接近。',
 13: '　若是再容许她靠近下去就危险了……相当危险。',
 14: '英之「也许是发生了什么吧？　毕竟她们不是会来找我倾诉各种事情的孩子。我这边也会找机会委婉地问一问」',
 15: '　我用手制止她，露出苦笑。自以为已经摆出了十二分的和善态度。',
 16: '英之「………唔！？」',
 20: '委員長「祷老师，怎么了吗？」',
 21: '英之「不，没什么」',
 26: '委員長「那么，我也该告辞了。失礼了」',
 27: '英之「啊…っ、唔！？　咳哼……也许是有什么烦恼吧。能请你不要太过声张吗」',
 29: '委員長「？　嗯，我当然会这么做」',
 30: '　在她行了一礼走出房间的背影上，晃动的马尾引人困意。',
 31: '　我心里清楚这不是能松懈下来的状况，却还是……。',
 33: '　不知是第几节课的铃声，传到了远离校舍的这个所在。究竟是第几节课呢。',
 34: '　在用时钟确认之前，我先低下了头。',
}

SKIP = set([22, 36, 37])


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'EL007'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    for i in work:
        if i in T:
            out['EL007#%d' % i] = wrap(orig.strings[i], T[i])
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing[:20])
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'EL007.json'), 'w', encoding='utf-8'),
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
    BADMAP = {'分', '那', '務', '察', '足', '走', '愚', '様', '怪', '助', '機', '辺',
              '捻', '諍', '殴', '菓', '嘘', '狙', '任', '投', '立', '細', '留',
              '首', '接'}
    for c in sorted(sus):
        if MERGED.get(c) in BADMAP:
            for k, v in out.items():
                if c in v:
                    print('  BAD', c, '->', MERGED.get(c), '|', k, '|', v[:60])
                    break


if __name__ == '__main__':
    main()
