#!/usr/bin/env python3
"""mktest.py — 构建测试/发布用游戏目录"""
import sys, os, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def build(dst, use_zh):
    src = os.path.join(ROOT, 'tenshi')
    data = os.path.join(ROOT, '.work', 'build' if use_zh else 'origbuild')
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(os.path.join(src, 'lcsebody.exe'), os.path.join(dst, 'lcsebody.exe'))
    shutil.copy2(os.path.join(data, 'lcsebody'), os.path.join(dst, 'lcsebody'))
    shutil.copy2(os.path.join(data, 'lcsebody.lst'), os.path.join(dst, 'lcsebody.lst'))
    for f in os.listdir(src):
        if f in ('lcsebody', 'lcsebody.lst', 'lcsebody.exe', 'Thumbs.db', 'sav'):
            continue
        if f.startswith('lcsebody.zip'):
            continue
        s = os.path.join(src, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst, f))
    sav = os.path.join(src, 'sav')
    if os.path.isdir(sav):
        shutil.copytree(sav, os.path.join(dst, 'sav'), dirs_exist_ok=True)
    print(f'built {dst}')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2] == 'zh' if len(sys.argv) > 2 else True)