#!/usr/bin/env python3
import os, hashlib
HERE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CN = os.path.join(HERE, 'cn')
TENSHI = os.path.join(HERE, 'tenshi')
ZH = os.path.join(HERE, '.work', 'zh')

# 1) lst 头部 hexdump
lst = open(os.path.join(CN, 'lcsebody.lst'), 'rb').read()
print('=== cn/lcsebody.lst 前 96 字节 hex (len=%d) ===' % len(lst))
print(lst[:96].hex())

# 2) cn vs tenshi 原版数据包
def md5f(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()
cnp = os.path.join(CN, 'lcsebody')
ttp = os.path.join(TENSHI, 'lcsebody')
print('\ncn/lcsebody 大小:', os.path.getsize(cnp) if os.path.exists(cnp) else '缺失')
print('tenshi/lcsebody 大小:', os.path.getsize(ttp) if os.path.exists(ttp) else '缺失')
if os.path.exists(ttp):
    print('cn  md5 :', md5f(cnp))
    print('tenshi md5 :', md5f(ttp))
    print('cn == tenshi (原版)?', md5f(cnp) == md5f(ttp))

# 3) zh json 文件大小与首字节
print('\n=== .work/zh/*.json 大小 ===')
for f in sorted(os.listdir(ZH)):
    if f.endswith('.json'):
        p = os.path.join(ZH, f)
        sz = os.path.getsize(p)
        head = open(p, 'rb').read(40)
        print('  %-22s %8d B  head=%s' % (f, sz, head[:40]))

# 4) 字节级取证：在 cn/lcsebody 里搜日文/中文标记
body = open(cnp, 'rb').read()
def find(label, s):
    enc = s.encode('cp932')
    probes = bytes(b ^ 0x02 for b in enc)  # 假设 XOR 0x02 加密
    n1 = body.count(probes)
    n2 = body.count(enc)                   # 也可能未加密
    print('  %-12s cp932=%s xor=%s 命中(加密=%d, 明文=%d)' % (label, enc.hex(), probes.hex(), n1, n2))
print('\n=== 关键字符串在 cn/lcsebody 的命中情况 ===')
find('です(日文)', 'です')
find('ます(日文)', 'ます')
find('天使(中文)', '天使')
find('秘事', '秘事')
find('中文', '中文')
find('LC-ScriptEngine(标题)', 'LC-ScriptEngine')
