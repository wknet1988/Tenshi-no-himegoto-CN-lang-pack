# -*- coding: utf-8 -*-
"""RCSL / RCLICK（存档·读档·回标题·退出 的确认对话框）译稿组装。
这是全包最后一处可注入的 UI 文本（10 串）。
注意：字符串形如 'No:' + \\x04\\x04\\x00\\x00\\x00 + 日文，
      \\x04 是插入存档编号的控制符，前缀必须原样保留，只替换日文尾巴。
"""
import json, os, sys
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

ZH_DIR = os.path.join('.work', 'zh')
PRE = 'No:' + '\x04\x04\x00\x00\x00'

T = {
 'RCSL#8':  PRE + '号存档。确定么？',
 'RCSL#9':  '确认',
 'RCSL#10': PRE + '号存档完毕',
 'RCSL#11': '确认',
 'RCSL#12': PRE + '号读档。确定么？',
 'RCSL#13': '确认',
 'RCLICK#7':  '返回标题。确定么？',
 'RCLICK#8':  '确认',
 'RCLICK#10': '要结束游戏么？',
 'RCLICK#11': '结束确认',
}

BADMAP = {'分', '那', '務', '察', '足', '走', '愚', '様', '怪', '助', '機', '辺', '捻', '諍',
          '殴', '菓', '嘘', '狙', '任', '投', '立', '細', '開', '留', '首', '接'}


def main():
    sys.path.insert(0, '.work')
    from to_jp import MERGED, drawable
    bad = []
    for k, v in T.items():
        for ch in v:
            if ch in '　「」…。、？！ー・ッNo:0123456789\x04\x00':
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

    out = {'RCSL': {}, 'RCLICK': {}}
    for name in out:
        o = Script(open(os.path.join('.work', 'extract', name), 'rb').read(), encoding='cp932')
        work = [i for i, s in enumerate(o.strings) if KANA.search(s)]
        keys = ['%s#%d' % (name, i) for i in work]
        missing = [k for k in keys if k not in T]
        extra = [k for k in T if k.startswith(name + '#') and k not in keys]
        print('%s 可译 %d | 缺失 %s | 多余 %s' % (name, len(work), missing, extra))
        assert not missing and not extra
        for i in work:
            out[name]['%s#%d' % (name, i)] = T['%s#%d' % (name, i)]

    for name, d in out.items():
        p = os.path.join(ZH_DIR, name + '.json')
        json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('-> %s (%d)' % (p, len(d)))


if __name__ == '__main__':
    main()
