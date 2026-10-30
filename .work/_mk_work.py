# -*- coding: utf-8 -*-
"""生成逐章底稿 .work/_<NAME>_work.txt（供人工定跳过边界）。

用法: python .work/_mk_work.py CM023 CM024 ...
格式: #<idx> [SENS]\t<原文>   （[SENS] = 检测器命中，误报率约 70%，须人工复核）
末尾打印块（间隔<=4 行视为同一场戏）供快速定位。
注：_audit_scripts 是脚本（无 __main__ 守卫），导入会跑全量审计，故只取其常量/函数。
"""
import sys, os, io, contextlib
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA

with contextlib.redirect_stdout(io.StringIO()):
    sys.path.insert(0, '.work')
    import _audit_scripts as A


def blocks(idxs, gap=4):
    out = []
    for i in sorted(idxs):
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def main(names):
    for n in names:
        p = os.path.join('.work', 'extract', n)
        o = Script(open(p, 'rb').read(), encoding='cp932')
        work = [i for i, s in enumerate(o.strings) if KANA.search(s)]
        flags = {}
        lines = []
        for i in work:
            s = o.strings[i]
            hits = A.flag_line(s)
            if hits:
                flags[i] = hits
            tag = ' [SENS]' if hits else ''
            lines.append('#%d%s\t%s' % (i, tag, s.replace('\n', ' ')))
        out = os.path.join('.work', '_%s_work.txt' % n.lower())
        open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
        bl = blocks(list(flags))
        print('== %s  可译 %d 行 | 标记 %d 处 | 块 %d' % (n, len(work), len(flags), len(bl)))
        for a, b in bl:
            cnt = sum(1 for i in flags if a <= i <= b)
            if cnt >= 3:
                print('   #%d-#%d (%d 行, %d 命中)' % (a, b, b - a + 1, cnt))
        print('   -> %s' % out)


if __name__ == '__main__':
    main(sys.argv[1:])
