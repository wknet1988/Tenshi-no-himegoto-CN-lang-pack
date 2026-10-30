# -*- coding: utf-8 -*-
"""EL003（退廃０４）译稿组装。
内容：英之在床上被罪恶感折磨→恶魔在他意识中低语诱惑→宣告『合为一体』
      →意识沉入漆黑之海→摩菜与綾夜袭（#43 起）。
边界：#43 起为未成年人主动的性描写，**全部跳过保留日文**；
      #4-#41 为内心独白与恶魔对话（无露骨描写），正常翻译。
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
 0: '退廃　　　０４　',
 4: '英之「唔…………っ」',
 5: '　我一倒在床上，身体便沉了下去，就这样，意识仿佛要沉入黑暗之中。',
 6: '　身体疲惫不堪，发出悲鸣的胸口渴求着……解脱。',
 7: '英之「可恶……っ！」',
 8: '　想要从这股痛苦中解脱出来。今天，我又一次因欲望而失去自我，伤害了重要的人。',
 9: '　我的头脑，记住了这一切。',
 10: '　起初还不太清晰的、沉溺于欲望的记忆。随着次数增加变得鲜明起来，抚过的肌肤触感留在指尖，吐出过的话语留在舌尖。',
 11: '　渐渐地，可憎的我与……这个我合为一体？　若是如此，如今痛苦着、责备着自己的这个我，又将何去何从。',
 12: '　如果就连这股罪恶感，终有一天也会消失的话。',
 14: '悪魔「你甘愿……一直做这么凄惨的自己吗？　应该不是吧」',
 16: '悪魔「可憎的，是现在的你」',
 18: '悪魔「我只是把你心中束缚着的多余之物，一点一点地解开而已」',
 19: '英之「……住手」',
 20: '　从我口中说出的，是确确实实的软弱之词。那是将恐惧如实说出口的话语。',
 21: '　我会消失……迄今为止积累起来的一切，都会。',
 23: '悪魔「我不会停手的。真可悲呢，英之」',
 25: '悪魔「好可爱……」',
 26: '　不同于睡意。违背着意志，眼皮紧紧闭合，将我关进黑暗之中。',
 28: '悪魔「只是舍弃不需要的东西罢了。我不会夺走什么，我会给你必要的东西」',
 29: '英之「必要的……」',
 31: '悪魔「与我合为一体吧」',
 36: '悪魔「相信我……呐，英之……我深爱着你」',
 37: '　自己的意识被好几只手臂拥住，仿佛要从身体里被抽离出去一般的感觉。',
 38: '　那是丧失感，也是诱惑。',
 40: '悪魔「我想要救你的」',
 41: '　向着比睡眠更深的、安稳的漆黑之海……笔直地坠落下去。',
}

# #43 起：摩菜・綾（未成年）的夜袭段落，全部保留日文
SKIP = set([43, 45, 46, 47, 49, 50, 52, 54, 56, 58, 60, 62, 63, 64,
            66, 68, 70, 71, 73, 75, 77, 79, 81, 83, 84])


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'EL003'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    for i in work:
        if i in T:
            out['EL003#%d' % i] = wrap(orig.strings[i], T[i])
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing[:20])
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'EL003.json'), 'w', encoding='utf-8'),
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
