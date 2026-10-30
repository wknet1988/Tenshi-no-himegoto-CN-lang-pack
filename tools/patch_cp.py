#!/usr/bin/env python3
"""
patch_cp.py — 给 exe 打编码补丁，强制引擎使用指定 codepage

用法:
  python patch_cp.py <src_exe> <dst_exe> <932|936>

补丁点（已逆向确认）：
  文件偏移 0x42c60:
    81 3d d4 66 4a 00 a4 03 00 00    cmp dword[0x4a66d4], 0x3A4   ; 932
  这是 DBCS 判别：==932 走 SJIS 表，否则走通用表。

  策略：把比较目标从 932 改成 936，引擎就会在 codepage==936 时
  选用 SJIS 那条 lead/trail 路径 —— 不够。

  更直接：0x42e63 的 codepage 解析函数
    8b 44 24 04                       mov eax,[esp+4]   ; 参数（可能是 CP_ACP 等）
    83 25 3c 66 4a 00 00              and dword[0x4a663c],0
    83 f8 fe                          cmp eax,0xFE   ; CP_OEMCP?
    ...
    ff 25 a8 86 4a 00                 jmp [GetACP]
  我们让该函数直接返回目标 codepage：b8 xx xx 00 00 90 c3
"""
import sys, struct, os

# codepage 解析函数入口（文件偏移 = RVA，因 .text RA==VA）
CP_FUNC = 0x42e63
# 备选：全局 codepage 变量被清零的初始化点（.data，RA==VA）
CP_GLOBAL_OFF = 0xa66d4


def patch_cp(src, dst, cp):
    b = bytearray(open(src, 'rb').read())
    orig = bytes(b[CP_FUNC:CP_FUNC + 7])
    # mov eax, <cp> ; nop ; ret
    b[CP_FUNC:CP_FUNC + 7] = bytes.fromhex('b8') + struct.pack('<I', cp) + b'\x90\xc3'
    new = bytes(b[CP_FUNC:CP_FUNC + 7])
    # 同时把 DBCS 判别处的常量同步为 cp
    b[0x42c67:0x42c6b] = struct.pack('<I', cp)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(bytes(b))
    print(f'{os.path.basename(src)} → {os.path.basename(dst)}  codepage={cp}')
    print(f'  @{CP_FUNC:#x}: {orig.hex(" ")}  ->  {new.hex(" ")}')
    print(f'  @{0x42c60:#x}: cmp 常量 -> {cp}')


if __name__ == '__main__':
    src, dst, cp = sys.argv[1], sys.argv[2], int(sys.argv[3])
    patch_cp(src, dst, cp)