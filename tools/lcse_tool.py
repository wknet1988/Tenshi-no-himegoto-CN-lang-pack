#!/usr/bin/env python3
"""
lcse_tool.py — LC-ScriptEngine (lcsebody) 解包 / 打包 / 字节码字符串工具

格式要点（已逆向验证）：
  .lst ：4字节头(记录数) + N×76 字节记录
        记录 = [offset:int32 ^0x01逐字节][size:int32 ^0x01逐字节]
               [name: 字符串部分 ^0x01，填充 0x00][unk:int32 原始]
        unk: 1 = 该文件被 XOR 0x02 加密（脚本/字节码）；3 = 原样数据（PNG 等）
  数据包 lcsebody：记录按索引顺序紧密排列，无间隙
  脚本字节码（XOR 0x02 解密后）：
        [count:int32][strings_space:int32][指令表 count*12 字节][字符串表][尾部残余]
        字符串表条目 = [len:int32][内容 len 字节][NUL]
  文本编码：Shift-JIS（引擎按系统 ACP 转换，可改用 GBK）
"""
import os, sys, struct

XOR_LST = 0x01
XOR_SCRIPT = 0x02
REC = 76


def x(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def _dec_name(raw64: bytes) -> str:
    z = raw64.find(b'\x00')
    b = raw64 if z < 0 else raw64[:z]
    b = x(b, XOR_LST)
    try:
        return b.decode('ascii')
    except UnicodeDecodeError:
        return b.decode('latin-1')


def _enc_name(name: str) -> bytes:
    b = x(name.encode('ascii', 'replace')[:63], XOR_LST)
    return b + b'\x00' * (64 - len(b))


def parse_lst(path):
    raw = open(path, 'rb').read()
    n = (len(raw) - 4) // REC
    recs = []
    for i in range(n):
        c = raw[4 + i * REC: 4 + (i + 1) * REC]
        o, s = struct.unpack('<ii', x(c[0:4], XOR_LST) + x(c[4:8], XOR_LST))
        recs.append({'offset': o, 'size': s, 'name': _dec_name(c[8:72]),
                     'unk': struct.unpack('<i', c[72:76])[0]})
    return recs


def build_lst(recs):
    # 头部计数同样 XOR 0x01（原始文件里是 6e 05 01 01 = 1135 ^ 0x01010101）
    out = bytearray(x(struct.pack('<i', len(recs)), XOR_LST))
    for r in recs:
        out += x(struct.pack('<ii', r['offset'], r['size']), XOR_LST)
        out += _enc_name(r['name'])
        out += struct.pack('<i', r['unk'])
    return bytes(out)


def extract(game_dir, out_dir):
    recs = parse_lst(os.path.join(game_dir, 'lcsebody.lst'))
    body = open(os.path.join(game_dir, 'lcsebody'), 'rb').read()
    for r in recs:
        d = os.path.join(out_dir, r['name'].replace('\\', os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        blob = body[r['offset']:r['offset'] + r['size']]
        if r['unk'] == 1:
            blob = x(blob, XOR_SCRIPT)
        open(d, 'wb').write(blob)
    return recs


def repack(game_dir, src_dir, lst_out=None, body_out=None):
    recs = parse_lst(os.path.join(game_dir, 'lcsebody.lst'))
    lst_out = lst_out or os.path.join(game_dir, 'lcsebody.lst')
    body_out = body_out or os.path.join(game_dir, 'lcsebody')
    body = bytearray()
    new = []
    for r in recs:
        p = os.path.join(src_dir, r['name'].replace('\\', os.sep))
        blob = open(p, 'rb').read()
        if r['unk'] == 1:
            blob = x(blob, XOR_SCRIPT)
        new.append(dict(r, offset=len(body), size=len(blob)))
        body += blob
    open(body_out, 'wb').write(bytes(body))
    open(lst_out, 'wb').write(build_lst(new))
    return new


# ---------------- 脚本字节码 ----------------
class Script:
    """解析并支持重写字符串表。传入的是已解密（已 XOR 0x02）的脚本字节。

    指令表原样保留；序列化时再 XOR 0x02 写回。
    """

    def __init__(self, raw, encrypted=False):
        self.raw = x(raw, XOR_SCRIPT) if encrypted else bytes(raw)
        self.count, self.sspace = struct.unpack('<ii', self.raw[0:8])
        self.inst = bytearray(self.raw[8:8 + self.count * 12])
        self.stbl_off = 8 + self.count * 12
        end = self.stbl_off + self.sspace
        self.strings = []
        p = self.stbl_off
        while p + 4 <= end:
            (n,) = struct.unpack('<i', self.raw[p:p + 4])
            p += 4
            if n < 0 or p + n > end:
                break
            b = self.raw[p:p + n]
            p += n
            if p < end and self.raw[p] == 0:
                p += 1
            self.strings.append(b.decode('cp932', 'replace'))
        self.str_end = p
        self.tail = bytes(self.raw[end:])
        self.encoding = 'cp932'

    # --- 字符串替换 API ---
    def enc(self, s):
        return s.encode(self.encoding, 'replace')

    def dec(self, b):
        return b.decode(self.encoding, 'replace')

    def rebuild(self, new_strings):
        self.strings = new_strings
        buf = bytearray()
        self.string_offsets = []
        for s in new_strings:
            b = self.enc(s)
            self.string_offsets.append(len(buf))
            buf += struct.pack('<i', len(b)) + b + b'\x00'
        self.string_table = bytes(buf)
        return self.string_offsets

    def serialize(self):
        out = bytearray(struct.pack('<ii', self.count, len(self.string_table)))
        out += self.inst
        out += self.string_table
        out += self.tail
        return x(bytes(out), XOR_SCRIPT)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'extract':
        os.makedirs(sys.argv[3], exist_ok=True)
        print(f'提取 {len(extract(sys.argv[2], sys.argv[3]))} 个文件 -> {sys.argv[3]}')
    elif cmd == 'repack':
        print(f'打包 {len(repack(sys.argv[2], sys.argv[3]))} 条记录')