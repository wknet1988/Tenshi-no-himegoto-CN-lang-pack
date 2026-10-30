# -*- coding: utf-8 -*-
"""EX002（退廃０７）译稿组装。
内容：英之在昏暗小室中等待摩菜・綾的『求め』，回想自己舍弃教职的经过→
      礼美（月岬）来访。
边界：#12/#16/#28/#29 与 #51 以后（对礼美——在校学生的身体接触与性描写）
      全部保留日文；可译的是开场独白（堕落自述）与两人初见的寒暄。
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
 0: '退廃　　　０７　',
 4: '　仰头望去，熏黑的天井加上房间本身的昏暗，实在阴森。',
 5: '　曾有一阵子，我还在外面的礼拜堂里、当着女生徒们的面装作授课的样子，如今回想起来却觉得是相当久远的事了。',
 6: '　是伸手也触及不到的、过去的话题。',
 7: '　学園的学生们现在，是用什么样的眼光看我的呢……若能把我当成工友一类的人来看待，倒还算好。',
 8: '　我再也回不去那个被称为教师的自己了。',
 9: '　正如摩菜和綾舍弃了社团与学业的校园生活、换取了替代品一般……我也舍弃了那个曾令自己憧憬、感到安宁的、作为教师的我。',
 10: '　不是被夺走，而是选择的结果。',
 11: '　今后大概也不会再带着难堪的表情在校内徘徊了吧。只要在察觉到摩菜与綾的『渴求』之时，直接前往二年级的教室就好。',
 13: '　为了随时应对可能发生的状况，我把背靠在沙发上，今天也在这个地方小睡。',
 15: '　这钟声意味着什么，我没有兴趣。',
 17: '　对我这样的我来说，那是毫无意义的事。',
 18: '　半开玩笑地从胸前拉出念珠，将手指缠绕在它的鎖上，垂在眼前。被施以特殊礼仪的银色念珠如镜面般闪耀，映出我的脸。',
 19: '　眺望着那张表情消失的自己的脸，也很快就厌倦了。',
 21: '　在这么早的时间点听到，大概是第几节课的休息时间结束了。继续在掌心转动念珠、怎么也不想放回胸前的我，把视线移回天井。',
 22: '　大大地打了个哈欠，准备再次……闭上眼睛。',
 24: '　实际上，是闭上了……意识大概也溶入了黑暗吧。轻微的敲门声，将它的意思传达给我的大脑，已是相当久之后的事了。',
 26: '礼美「………祷老师在吗」',
 27: '　映在念珠上的我笑了。只有嘴角，丑陋地歪斜着。',
 35: '礼美「老、祷老师……！？　日安。一声不吭就打开门，我会吓到的呀」',
 36: '　缩着身子，彼女站在门前。环顾四周确认没有任何人的身影之后，我才重新把视线移回彼女脸上。',
 37: '英之「找我有什么事吗？　吃惊的是我这边哦。我还以为汝讨厌我呢」',
 41: '礼美「……屡屡失礼，我向汝致歉。那一次的事」',
 42: '英之「是在有自觉的前提下，才那样看着我的吧」',
 44: '礼美「………我之前也应该道过歉了。我以为，汝已经不追究了」',
 45: '　这不是彼女任性的说辞，我想起来了。摩菜与我、三人相拥的那一天……彼女曾用像是乞求般的目光看着我呢。',
 46: '英之「是啊，我们互相理解了……我把最关键的事给忘了」',
 50: '礼美「忘了…………ッ！？」',
}

SKIP = set([12, 16, 28, 29]) | set(range(51, 168))


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'EX002'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    for i in work:
        if i in T:
            out['EX002#%d' % i] = wrap(orig.strings[i], T[i])
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing[:20])
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'EX002.json'), 'w', encoding='utf-8'),
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
