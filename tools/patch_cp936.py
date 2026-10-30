#!/usr/bin/env python3
"""
patch_cp936.py — 把引擎的「文本 codepage」固定为 936 (GBK)

原理（已逆向确认）：
  引擎在把脚本文本转成 Unicode 时，会这样取 codepage：
      cmp  [ebp+18], 0
      jnz  +8
      mov  eax, [0x4a63ac]     ; CP_TEXT —— 文本 codepage
      mov  [ebp+18], eax
      ...
      push [ebp+18]             ; CodePage 参数
      call [MultiByteToWideChar]

  CP_TEXT (0x4a63ac) 由剧情脚本初始化时写入（日文版 = 932），
  导致我们写入的 GBK 中文被按 Shift-JIS 解码 → 乱码。

  修法：把「读 CP_TEXT」这条指令替换成「mov eax, 936」。
  `a1 ac 63 4a 00`（mov eax,[0x4a63ac]，5 字节）
  → `b8 a8 03 00 00`（mov eax,0x3a8，  5 字节）   ← 等长，不影响任何跳转/偏移

用法:
  python patch_cp936.py <src_exe> <dst_exe>
"""
import sys, os, struct

CP_TEXT_ADDR = 0x4a63ac
READ_PATTERN = bytes.fromhex('a1ac634a00')      # mov eax,[0x4a63ac]
CP936_PATTERN = bytes.fromhex('b8a8030000')     # mov eax,0x000003a8

# 这些点后面必须紧跟 mov [ebp+xx],eax —— 确认是「取 codepage 存局部变量」
FOLLOW_MOV = {bytes.fromhex('8945fc'),   # 0x3be2b  存到 [ebp-4]
              bytes.fromhex('894520'),   # 0x3c298
              bytes.fromhex('894518'),   # 0x42b05 / 0x459c0 / 0x462e9 / 0x46400
              bytes.fromhex('894520')}   # 0x46656


def patch(src, dst):
    b = bytearray(open(src, 'rb').read())
    hits, st = [], 0
    while True:
        k = b.find(READ_PATTERN, st)
        if k < 0 or k > 0x80000:
            break
        hits.append(k)
        st = k + 1

    applied = []
    for k in hits:
        follow = bytes(b[k + 5:k + 8])
        # 0x42e9d 是判断分支（比较 == -4），语义不同，跳过
        if follow in FOLLOW_MOV:
            b[k:k + 5] = CP936_PATTERN
            applied.append((k, follow.hex()))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(bytes(b))
    print(f'扫描 {len(hits)} 处 CP_TEXT 读取，打补丁 {len(applied)} 处：')
    for k, fl in applied:
        print(f'  {k:#08x}  mov eax,[CP_TEXT] → mov eax,936   (后继 {fl})')
    print(f'输出 -> {dst}')
    return applied


if __name__ == '__main__':
    patch(sys.argv[1], sys.argv[2])