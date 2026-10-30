#!/usr/bin/env python3
"""
cp_probe.py — 用 IAT hook 观察游戏实际调用的 codepage 相关 API
在游戏进程外无法 ReadProcessMemory，改用简单的 DLL 注入方式不可靠；
这里采用替代方案：直接 patch exe 的多个候选点，各跑一次看哪个让日文变中文/乱码。
"""
import sys, os, struct, shutil, subprocess, time, ctypes

SRC = os.path.join('tenshi', 'lcsebody.exe')


def load(path):
    return bytearray(open(path, 'rb').read())


def save(b, path):
    with open(path, 'wb') as f:
        f.write(bytes(b))


def patch_cpinit(b):
    """
    0x42e63: 8b 44 24 04            mov eax,[esp+4]
    改成:   b8 a8 03 00 00 c3        mov eax,0x3a8 ; ret
    → 函数直接返回 936，不再调 GetACP
    但注意这个函数的返回值就是 codepage，且会跳过后续初始化。
    更精准：只让它总是返回 936。
    """
    off = 0x42e63
    orig = bytes(b[off:off + 7])
    print('  orig @0x42e63:', orig.hex(' '))
    # mov eax,0x3a8 (5 bytes) + nop + ret -> 7 bytes
    new = bytes.fromhex('b8a8030000') + b'\x90\xc3'
    b[off:off + 7] = new
    print('  new  @0x42e63:', bytes(b[off:off + 7]).hex(' '))
    return orig


def patch_cmp932to936(b):
    """
    0x42c60: 81 3d d4664a00 a4030000   cmp dword[0x4a66d4], 932
    改成比较 936 → 让 DBCS 路径选择走 GBK 表
    """
    off = 0x42c60
    print('  orig @0x42c60:', bytes(b[off:off + 10]).hex(' '))
    b[off + 7:off + 10] = struct.pack('<I', 0x3a8)  # a4 03 00 00 -> a8 03 00 00
    print('  new  @0x42c60:', bytes(b[off:off + 10]).hex(' '))


if __name__ == '__main__':
    print('patch tool loaded')