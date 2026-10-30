#!/usr/bin/env python3
"""
lcse_script.py — LC-ScriptEngine 脚本字节码的解析 / 修改 / 序列化

已验证的格式（以 OP001 为准，2198 条指令 / 428 个字符串）：
  文件 = [count:i32][strings_space:i32][指令表 count×12B][字符串表 strings_space B][尾部]
  指令 = [opcode:u8][pad:3B][arg1:i32][arg2:i32]
  字符串表条目 = [len:i32][内容 len 字节，末字节为 NUL]   （len 含 NUL）
  字符串引用：opcode=0x11 且 arg1=2 时，arg2 = 目标字符串在字符串表内的偏移
              （428 条 push-string 指令 ↔ 428 个字符串条目，一一对应）
"""
import struct
from lcse_tool import x, XOR_SCRIPT

OP_PUSH_STR = 0x11


class Script:
    def __init__(self, raw, encoding='cp932'):
        self.raw = bytes(raw)
        self.encoding = encoding
        self.count, self.sspace = struct.unpack('<ii', self.raw[0:8])
        self.inst = bytearray(self.raw[8:8 + self.count * 12])
        self.stbl_off = 8 + self.count * 12
        self._parse()
        self.new_strings = list(self.strings)

    def _parse(self):
        end = self.stbl_off + self.sspace
        p = self.stbl_off
        self.offsets, self.strings = [], []
        while p + 4 <= end:
            (n,) = struct.unpack('<i', self.raw[p:p + 4])
            if n < 0 or p + 4 + n > end:
                break
            self.offsets.append(p - self.stbl_off)
            b = self.raw[p + 4:p + 4 + n]
            self.strings.append(b[:-1].decode(self.encoding, 'replace') if n else '')
            p += 4 + n
        self.tail = self.raw[end:]
        self.offset_of = {o: i for i, o in enumerate(self.offsets)}

    # --- 反汇编 ---
    def push_refs(self):
        """返回 [(指令下标, 字符串下标)]，即所有显示字符串的引用关系。"""
        out = []
        for i in range(self.count):
            b = self.inst[i * 12:(i + 1) * 12]
            if b[0] == OP_PUSH_STR and struct.unpack('<i', b[4:8])[0] == 2:
                off = struct.unpack('<i', b[8:12])[0]
                if off in self.offset_of:
                    out.append((i, self.offset_of[off]))
        return out

    # --- 修改 ---
    def set_strings(self, mapping):
        """mapping: {字符串下标: 新文本}"""
        for k, v in mapping.items():
            self.new_strings[k] = v

    def serialize(self):
        buf = bytearray()
        new_off = []
        for s in self.new_strings:
            b = s.encode(self.encoding, 'replace') + b'\x00'
            new_off.append(len(buf))
            buf += struct.pack('<i', len(b)) + b
        # 重建字符串表偏移并回填指令
        off_to_idx = {o: i for i, o in enumerate(new_off)}
        for i in range(self.count):
            b = self.inst[i * 12:(i + 1) * 12]
            if b[0] == OP_PUSH_STR and struct.unpack('<i', b[4:8])[0] == 2:
                old = struct.unpack('<i', b[8:12])[0]
                if old in self.offset_of:
                    idx = self.offset_of[old]
                    self.inst[i * 12 + 8:i * 12 + 12] = struct.pack('<i', new_off[idx])
        out = bytearray(struct.pack('<ii', self.count, len(buf)))
        out += self.inst
        out += buf
        out += self.tail
        return bytes(out)   # 明文（未 XOR 0x02）；写盘/打包时再加密


def load(path, encoding='cp932'):
    return Script(open(path, 'rb').read(), encoding)


def loads(raw, encoding='cp932'):
    """raw 为磁盘上的密文（XOR 0x02）字节"""
    return Script(x(raw, XOR_SCRIPT), encoding)


def save(sc, path):
    open(path, 'wb').write(x(sc.serialize(), XOR_SCRIPT))