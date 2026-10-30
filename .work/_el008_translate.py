# -*- coding: utf-8 -*-
"""EL008（退廃１１）译稿组装。
内容：英之带委員長等四名女生徒深入无人的一年级教室→门窗自锁、恶魔之力
      浸透→与恶魔『同化』完成→少女们被束缚→突入四人轮戏。
边界：本章为未成年学生为对象的侵犯场景，可译部分仅限前段『舞台布置』与
      『同化』相关的恶魔对话。跳过：
      #34（束缚后喘息）、#48（受け入れて 性暗示）、#55（与摩菜作比较的
      身体评价）、#64/#65（『楽しみましょう』侵犯前奏）、#68（恐惧发抖的
      身体描写）、#76（数人数）、#77 以后（四人轮戏实戏段 / #96 收尾）。
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
 0: '退廃　　　１１　',
 4: '　一间间地张望着路过的教室，逆着走向升降口的学生人潮前行。',
 5: '　校舎很大。走着走着，走廊上的学生渐渐少了，',
 9: '委員長「祷老师是要去何处呢……」',
 10: '　终于彻底看不见了。',
 11: '英之「啊，已经到了」',
 12: '　走到尽头的那间空无一人的教室，位于一年级楼层的深处，离楼梯也很远。',
 13: '　会是一处绝佳的舞台吧。',
 20: '委員長「教室？　那个，祷老师……」',
 21: '　试着拉开门，似乎确实还作为教室在使用，室内整齐地摆放着一张张书案。然而所有学生都已放学回去了。',
 22: '　每一张书案旁，都没有挂着书包。',
 23: '英之「什么……我在想，要不要给你们上一堂课呢」',
 26: '女生徒Ｂ「什么……っ！？」',
 27: '　万一也不希望有人来打扰啊……仅仅是这么一想，教室的门与窗便猛地关上，自内侧锁死了。',
 28: '　教室的每个角落，都被并非我的某个存在的力量所浸透。',
 30: '悪魔「不，不对……这已经是英之的力量了哦。是我与英之的力量」',
 32: '女生徒Ｃ「啊！？　啊ッ、啊……啊啊啊」',
 33: '　露出惧色、作势要逃的女生徒们，一经我送去视线，便停下了所有的动作。',
 35: '英之「原来如此，啊」',
 36: '　所谓合为一体，就是这么一回事吗。',
 38: '悪魔「再把心敞开一些。直到指尖……每个角落都要接纳我」',
 39: '英之「就像你所做的那样，我也能做到……？」',
 41: '悪魔「唔，因为英之与我是一体的嘛」',
 42: '英之「……哼哼」',
 44: '委員長「什么？　你在说什么啊，祷老师」',
 45: '　进来了……我的身体，直到心的深处，另一个意志。',
 46: '　也曾有过一门心思想要消灭你的时候啊……你。',
 49: '　就像一旦混在一起的颜色，便无法再变回别的颜色一样。我们交融在一起。',
 51: '悪魔「我等了很久。非常、非常漫长的时间……一直在等」',
 52: '　我看得见啊……所缠绕着的，鲜艳的血色。',
 53: '　完全的『同化』……其含义，我身上仅存的作为圣职者的那一部分还明白。以我为养分，『那家伙』……不，是她获得了力量。',
 57: '悪魔「这就是我……与英之合为一体的我哦」',
 58: '英之「唔……」',
 60: '悪魔「约定，终于实现了呢……如此一来我们便能永远在一起。永远，永远哦」',
 61: '　那是一副什么样的眼神呢，是在害怕吗？她们……一副好像以为自己会被吃掉一般的神情。',
 62: '　莫非，她们把我当成了怪物吗。',
 67: '女生徒Ｄ「我、我……我」',
 69: '　被从胸中传来的笑声所勾引。',
 71: '悪魔「就连神都能当呢，我们……」',
 72: '　真是狂妄的说法……我这么想。还留在这里的我，依然尊崇着神这个字眼。',
 73: '　对那种事，我没有兴趣。',
 75: '悪魔「唔，英之做自己想做的事就好」',
}

SKIP = set([34, 48, 55, 64, 65, 68, 76,
            77, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 96])


def main():
    orig = Script(open(os.path.join('.work', 'extract', 'EL008'), 'rb').read(),
                  encoding='cp932')
    work = [i for i, s in enumerate(orig.strings) if KANA.search(s)]
    out = {}
    for i in work:
        if i in T:
            out['EL008#%d' % i] = wrap(orig.strings[i], T[i])
    missing = [i for i in work if i not in SKIP and i not in T]
    if missing:
        print('!! 未提供译文下标:', missing[:20])
        sys.exit(1)
    for i in T:
        if i not in work:
            print('!! 多余条目(不可译或不存在): #%d' % i)
            sys.exit(1)
    os.makedirs(ZH_DIR, exist_ok=True)
    json.dump(out, open(os.path.join(ZH_DIR, 'EL008.json'), 'w', encoding='utf-8'),
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
