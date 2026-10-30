#!/usr/bin/env python3
"""
makedef.py — 生成 DLL 代理所需的 .def 文件
从游戏 exe 的导入表自动提取 kernel32.dll 的全部导入函数名。
除我们拦截的几个之外，其余全部 FORWARD 到真正的 kernel32。
"""
import struct, os, sys

EXE = sys.argv[1] if len(sys.argv) > 1 else 'tenshi/lcsebody.exe'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'tools/cp936proxy.def'

# 我们自己实现（拦截）的函数
HOOK = {
    'MultiByteToWideChar',
    'WideCharToMultiByte',
    'GetCPInfo',
    'GetStringTypeA',
    'GetDBCSLeadByteEx',
}

b = open(EXE, 'rb').read()
pe = struct.unpack('<I', b[0x3c:0x40])[0]
nsec = struct.unpack('<H', b[pe + 6:pe + 8])[0]
optsz = struct.unpack('<H', b[pe + 20:pe + 22])[0]
sec = pe + 24 + optsz
secs = []
for i in range(nsec):
    o = sec + i * 40
    vs, va, rs, ra = struct.unpack('<IIII', b[o + 8:o + 24])
    secs.append((va, vs, ra))


def f2rva(f):
    for va, vs, ra in secs:
        if va <= f < va + max(vs, rs):
            return ra + (f - va)
    return None


dll_off = None
off = 0x400  # .idata 附近，直接扫描 IMAGE_IMPORT_DESCRIPTOR
# 从 DataDirectory[1] 取导入表 RVA
dd = pe + 24 + 96 + 8  # PE32: DataDirectory starts at pe+24+96; import = index1
imp_rva, imp_sz = struct.unpack('<II', b[dd:dd + 8])
imp_off = f2rva(imp_rva)
print('Import Directory RVA', hex(imp_rva), '-> file', hex(imp_off))

kernel32 = None
o = imp_off
while True:
    oft, ts, fc, name_rva, ft = struct.unpack('<5I', b[o:o + 20])
    if oft == 0 and name_rva == 0:
        break
    no = f2rva(name_rva)
    dll = b[no:no + 64].split(b'\x00')[0].decode('latin1')
    fto = f2rva(ft)
    idx = 0
    fns = []
    while True:
        v = struct.unpack('<I', b[fto + idx * 4:fto + idx * 4 + 4])[0]
        if v == 0:
            break
        if not (v & 0x80000000):
            fn = b[f2rva(v) + 2:f2rva(v) + 66].split(b'\x00')[0].decode('latin1')
            fns.append(fn)
        idx += 1
    if 'MultiByteToWideChar' in fns:
        kernel32 = fns
        print('found kernel32 with', len(fns), 'functions')
        break
    o += 20

if not kernel32:
    print('ERROR: kernel32 not found')
    raise SystemExit(1)

lines = ['LIBRARY cp936proxy', 'EXPORTS']
hooked, forwarded = [], []
for fn in kernel32:
    if fn in HOOK:
        lines.append('    %s' % fn)
        hooked.append(fn)
    else:
        lines.append('    %s=kernel32.%s' % (fn, fn))
        forwarded.append(fn)
# 额外可能被间接用到的
for extra in ('GetDBCSLeadByteEx', 'GetStringTypeExA', 'GetStringTypeW',
              'IsValidCodePage', 'LCMapStringA'):
    if extra not in kernel32 and extra not in HOOK:
        lines.append('    %s=kernel32.%s' % (extra, extra))
        forwarded.append(extra)

open(OUT, 'w').write('\n'.join(lines) + '\n')
print('\n写出', OUT)
print('  自实现(拦截):', hooked)
print('  转发:', len(forwarded), '个')
missing = HOOK - set(kernel32)
if missing:
    print('  注意: 以下拦截目标不在导入表里(仍会导出，供 GetProcAddress 使用):', missing)