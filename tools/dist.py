#!/usr/bin/env python3
"""dist.py — 生成汉化补丁包

用法:
    python tools/dist.py            # 只出补丁 + 工具链（默认）
    python tools/dist.py --full     # 另外生成完整可运行目录（约 1 GB，慎用）

产物（汉化补丁/）:
    天使のひめごと-汉化补丁.zip    lcsebody + lcsebody.lst + 安装说明 + 文件校验
    汉化工具链.zip                tools/ + 译稿脚本 + 译文 JSON + 翻译规范
"""
import os, sys, shutil, zipfile, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
GAME = os.path.join(ROOT, 'tenshi')
BUILD = os.path.join(ROOT, '.work', 'build')
DIST = os.path.join(ROOT, '汉化补丁')
FULL = os.path.join(ROOT, '天使のひめごと-汉化版')
README = os.path.join(ROOT, '.work', 'README.txt')

FILES = ['lcsebody', 'lcsebody.lst']


def digest(path):
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest(), os.path.getsize(path)


def manifest():
    lines = ['天使のひめごと 汉化补丁 — 文件校验', '=' * 40, '']
    for f in FILES:
        m, s, n = digest(os.path.join(BUILD, f))
        lines += [f, '  大小    : %d 字节 (%.1f MB)' % (n, n / 1024 / 1024),
                  '  MD5     : %s' % m, '  SHA-256 : %s' % s, '']
    lines += ['说明: 覆盖后可用以上值核对游戏目录内的同名文件是否一致。', '']
    return '\n'.join(lines)


def make_patch():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    zp = os.path.join(DIST, '天使のひめごと-汉化补丁.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in FILES:
            z.write(os.path.join(BUILD, f), f)
        if os.path.exists(README):
            z.write(README, '安装说明.txt')
        else:
            print('!! 缺少 .work/README.txt，补丁内将没有说明文件')
        z.writestr('文件校验.txt', manifest().encode('utf-8-sig'))
    print('补丁   -> %s  (%.1f MB)' % (zp, os.path.getsize(zp) / 1024 / 1024))


def make_tools():
    """工具链 + 译稿脚本 + 译文，便于后续维护或接续汉化"""
    z = os.path.join(DIST, '汉化工具链.zip')
    n = 0
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as f:
        for fn in sorted(os.listdir(HERE)):
            if fn.endswith('.py'):
                f.write(os.path.join(HERE, fn), 'tools/' + fn)
                n += 1
        work = os.path.join(ROOT, '.work')
        for fn in sorted(os.listdir(work)):
            if fn.endswith('.py') and fn.startswith('_'):
                f.write(os.path.join(work, fn), '译稿脚本/' + fn)
                n += 1
        for d, sub in ((os.path.join(work, 'zh'), '译文'),
                       (os.path.join(work, 'sheets'), '翻译表')):
            if os.path.isdir(d):
                for fn in sorted(os.listdir(d)):
                    f.write(os.path.join(d, fn), '%s/%s' % (sub, fn))
                    n += 1
        g = os.path.join(work, 'TRANSLATION_GUIDE.md')
        if os.path.exists(g):
            f.write(g, '翻译规范.md')
        p = os.path.join(work, 'cm_progress.txt')
        if os.path.exists(p):
            f.write(p, '汉化进度日志.txt')
    print('工具链 -> %s  (%d 个文件, %.0f KB)' % (z, n, os.path.getsize(z) / 1024))


def make_full():
    if os.path.exists(FULL):
        shutil.rmtree(FULL)
    os.makedirs(FULL)
    for f in sorted(os.listdir(GAME)):
        if f in FILES or f.startswith('lcsebody.zip'):
            continue
        s = os.path.join(GAME, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(FULL, f))
    for f in FILES:
        shutil.copy2(os.path.join(BUILD, f), os.path.join(FULL, f))
    if os.path.exists(README):
        shutil.copy2(README, os.path.join(FULL, '汉化说明.txt'))
    sav = os.path.join(GAME, 'sav')
    if os.path.isdir(sav):
        shutil.copytree(sav, os.path.join(FULL, 'sav'))
    print('完整版 -> %s' % FULL)


if __name__ == '__main__':
    make_patch()
    make_tools()
    if '--full' in sys.argv:
        make_full()
