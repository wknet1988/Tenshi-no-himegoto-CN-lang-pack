# -*- coding: utf-8 -*-
"""AY011（綾线第 10 章）译稿组装。
内容：深夜，摩菜在庭院（綾与英之方才亲密之处）掘土，被归来的伊莉娜撞见并对峙，
      伊莉娜拔刃却未下手，独自权衡是否在此出手（顾虑「伊诺里」察觉）。
SKIP={38,42}：摩菜（儿童）察觉兄长与綾之性行，属未成年相关，留日文。
术语：英之/摩菜/綾/伊莉娜(说话人字段保留片假名 イリーナ)/伊诺里(イノリ)/意大利(イタリア)。
綾自称保留片假名「あや」（本章未出现）；摩菜/綾/英之原名即为汉字，沿用。
パイルバンカー 为固有武器名，保留片假名。
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
 0: '綾　　　　１０　',
 6: 'イリーナ「……在那般地方，你在做什么」',
 10: '摩菜「…………？」',
 12: 'イリーナ「这般深夜，连鞋也未穿便来到庭院。那棵树下，莫非有什么」',
 13: '　方才綾与英之相拥的那处地方，摩菜正伏身其间，将手指探向仍带湿气的地面——此刻她抬起了脸。',
 15: '摩菜「……………………」',
 19: 'イリーナ「……………你，仍是摩菜么」',
 23: '摩菜「烦死了」',
 27: 'イリーナ「！　…………」',
 28: '　将长外套的下摆向后扬起，腰肢微微下沉。摩菜以玻璃珠般的眼睛，凝视着イリーナ毫无停顿地转入战斗姿态。',
 32: '摩菜「伊莉娜小姐？　怎会，你不是回意大利去了么」',
 36: 'イリーナ「…？」',
 44: 'イリーナ「摩菜、你……」',
 48: '摩菜「……………………什么？」',
 50: 'イリーナ「！」',
 51: '　后退半步的イリーナ，以不足一秒的速度卷起右袖。盖着手背至肘间的白银パイルバンカー的刃尖，精准地指向摩菜眉间……然而。',
 55: '摩菜「……ッ」',
 56: '　全然不以为意。唯……摩菜按住太阳穴，摇摇晃晃地走在庭院，朝那扇未闭的窗口倒去，将上身伏进其中。',
 57: '　刃尖朝向那毫无防备的背影……。',
 61: 'イリーナ「……ふぅ」',
 62: '　不久，面朝地面。',
 66: 'イリーナ「…看来，不见面便回去方为上策。虽已无多余裕……但若在此动手，会被伊诺里发现」',
 70: 'イリーナ「明日么……在那之前，能维持『如今这般』便好」',
 74: 'イリーナ「伊诺里会怒，也会恨我罢」',
 78: 'イリーナ「…………无论如何，都是避不了的事么」',
}

SKIP = {38, 42}

BADMAP = {'分', '那', '務', '察', '足', '走', '愚', '様', '怪', '助', '機', '辺', '捻', '諍',
          '殴', '菓', '嘘', '狙', '任', '投', '立', '細', '開', '留', '首', '接'}


def main():
    o = Script(open(os.path.join('.work', 'extract', 'AY011'), 'rb').read(), encoding='cp932')
    work = [i for i, s in enumerate(o.strings) if KANA.search(s)]
    target = [i for i in work if i not in SKIP]
    missing = [i for i in target if i not in T]
    extra = [k for k in T if k not in target]
    print('可译 %d | 目标 %d | 缺失 %s | 多余 %s' % (len(work), len(target), missing, extra))
    assert not missing and not extra

    sys.path.insert(0, '.work')
    from to_jp import MERGED, drawable
    bad = []
    for k, v in T.items():
        for ch in v:
            if ch in '　「」…。、？！ー・ッふぅイリーナパイルバンカー':
                continue
            if not drawable(ch) and ch not in MERGED:
                bad.append((k, ch))
    print('无解字:', sorted(set(c for _, c in bad)) or '无')
    warn = []
    for k, v in T.items():
        for ch in v:
            if ch in MERGED and MERGED[ch] in BADMAP:
                warn.append((k, ch, MERGED[ch]))
    print('坏映射告警:', warn or '无')

    out = {}
    for i in target:
        out['AY011#%d' % i] = wrap(o.strings[i], T[i])
    json.dump(out, open(os.path.join(ZH_DIR, 'AY011.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('-> %s (%d)' % (os.path.join(ZH_DIR, 'AY011.json'), len(out)))


if __name__ == '__main__':
    main()
