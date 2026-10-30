#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""准备阶段：重建干净日文底稿 + 修复译文目录。"""
import os, sys, shutil, json
HERE = os.path.abspath('.')
sys.path.insert(0, os.path.join(HERE, 'tools'))
from lcse_tool import extract

print('== 1) 重新解包 tenshi 原版 -> .work/extract (干净日文底稿) ==')
n = len(extract('tenshi', os.path.join('.work', 'extract')))
print('   extract 文件数:', n)

print('== 2) 修复译文目录 .work/zh ==')
ZH = '.work/zh'
ZB = '.work/zh_backup'
COR = '.work/zh/_corrupted'
os.makedirs(COR, exist_ok=True)
backup = {f for f in os.listdir(ZB) if f.endswith('.json')}

moved = kept_valid = 0
for f in sorted(os.listdir(ZH)):
    if not f.endswith('.json') or f in backup:
        continue
    p = os.path.join(ZH, f)
    raw = open(p, 'rb').read()
    if raw.strip(b'\x00') == b'':
        shutil.move(p, os.path.join(COR, f)); moved += 1
        print('   移走(全零损坏):', f)
    else:
        try:
            json.loads(raw); kept_valid += 1
            print('   跳过(非空且可解析, 不在backup):', f)
        except Exception:
            shutil.move(p, os.path.join(COR, f)); moved += 1
            print('   移走(损坏非空):', f)
print('   移走损坏译文:', moved, '| 保留的有效非backup文件:', kept_valid)

restored = 0
for f in sorted(backup):
    shutil.copy(os.path.join(ZB, f), os.path.join(ZH, f)); restored += 1
print('   从 zh_backup 恢复译文:', restored, sorted(backup))
print('\n准备阶段完成。')
