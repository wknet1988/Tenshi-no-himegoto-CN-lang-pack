#!/usr/bin/env python3
"""
build_zh.py — 注入中文译文 + 字体替换 + 打包 lcsebody / lst

数据流约定（.work/extract/ 里统一存【明文】已解密的脚本）：
  extract()   数据包 --XOR 0x02--> extract/（明文）
  inject()    extract/（明文）--注入译文--> extract/（仍是明文）
  repack_all() extract/（明文）--XOR 0x02--> build/lcsebody（密文）
"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lcse_script import Script
from lcse_tool import parse_lst, build_lst, x, XOR_SCRIPT

ROOT = os.path.abspath(os.path.join(HERE, '..'))
EXTRACT = os.path.join(ROOT, '.work', 'extract')
ZHDIR = os.path.join(ROOT, '.work', 'zh')
OUT = os.path.join(ROOT, '.work', 'build')

# Read the original scripts as Shift-JIS and write them back the same way.
# The engine walks string bytes with Shift-JIS rules and asks GDI for glyphs by
# byte value, so the localized text must stay inside the Shift-JIS range.
# tools/to_jp.py has already mapped every simplified-only character onto a
# traditional/Japanese glyph that Shift-JIS can encode.
ENC_SRC = 'cp932'
ENC_DST = 'cp932'

# 字体名替换：日文字体在中文系统下无中文字形，换成宋体
# 字体名一律用纯 ASCII（SimSun = 宋体的英文名）。
# 理由：引擎拿到字体名后可能自行按 SJIS 解析，GBK 字节会被误判为双字节字符；
# ASCII 名在任何代码页下都是同一串字节，最稳妥。
# 字体名保持原样。MＳ ゴシック 属于 JIS X 0208，在 Shift-JIS 下可正确解析，
# 且其中的汉字字形足以显示本项目的译文（已全部映射到日文汉字）。
# 字体名保持原样。MＳ ゴシック 属于 JIS X 0208，在 Shift-JIS 下可正确解析，
# 且其中的汉字字形足以显示本项目的译文（已全部映射到日文汉字）。
FONT_MAP = {
    'ＭＳ 明朝': 'ＭＳ 明朝',
}


def check_encodable(name):
    """检查把所有字符串转成 GBK 是否可行"""
    sc = Script(open(os.path.join(EXTRACT, name), 'rb').read(), encoding=ENC_SRC)
    bad = []
    for i, s in enumerate(sc.strings):
        try:
            s.encode(ENC_DST)
        except UnicodeEncodeError:
            bad.append((i, s[:30]))
    return len(bad), bad


def inject():
    """Inject the translation and swap font names.

    Both steps have to happen in one pass. A script is parsed once as
    Shift-JIS (the encoding the original data uses), the replacement strings
    are assigned, and only then is the script re-encoded to GBK and written
    back. Serializing in between corrupts every string that was not
    translated: the original Japanese would be encoded as GBK and come out as
    question marks.
    """
    total = 0
    font_hits = 0

    # Load every translation up front.
    tr = {}
    for zp in sorted(glob.glob(os.path.join(ZHDIR, '*.json'))):
        fname = os.path.basename(zp)[:-5]
        tr[fname] = {}
        for k, v in json.load(open(zp, encoding='utf-8')).items():
            idx = int(k.split('#')[1])
            tr[fname][idx] = v

    for name in sorted(os.listdir(EXTRACT)):
        p = os.path.join(EXTRACT, name)
        if not os.path.isfile(p):
            continue
        try:
            sc = Script(open(p, 'rb').read(), encoding=ENC_SRC)
        except Exception:
            continue

        changed = 0
        # Font names first: they apply to translated and untranslated entries.
        for i, s in enumerate(sc.strings):
            t = s
            for jp, cn in FONT_MAP.items():
                if jp in t:
                    t = t.replace(jp, cn)
            if t != s:
                sc.new_strings[i] = t
                changed += 1
                font_hits += 1

        # Then the translation.
        applied = 0
        for idx, text in tr.get(name, {}).items():
            if 0 <= idx < len(sc.strings):
                sc.new_strings[idx] = text
                applied += 1

        if changed or applied:
            sc.encoding = ENC_DST
            with open(p, 'wb') as f:
                f.write(sc.serialize())
            total += applied
            print(f'  {name}: {applied} 条译文'
                  + (f' + {changed} 处字体名' if changed else ''))

    print(f'共注入 {total} 条译文，字体名替换 {font_hits} 处')


def repack_all():
    game = os.path.join(ROOT, 'tenshi')
    recs = parse_lst(os.path.join(game, 'lcsebody.lst'))
    os.makedirs(OUT, exist_ok=True)
    new = []
    outp = os.path.join(OUT, 'lcsebody')
    off = 0
    # 流式写盘：避免把整个数据包累积在内存（239MB 级会 MemoryError）
    with open(outp, 'wb') as f:
        for r in recs:
            p = os.path.join(EXTRACT, r['name'].replace('\\', os.sep))
            blob = open(p, 'rb').read()
            if r['unk'] == 1:
                blob = x(blob, XOR_SCRIPT)
            new.append(dict(r, offset=off, size=len(blob)))
            f.write(blob)
            off += len(blob)
    with open(os.path.join(OUT, 'lcsebody.lst'), 'wb') as f:
        f.write(build_lst(new))
    print(f'打包完成 -> {OUT}  ({off} 字节, {len(new)} 条记录)')


if __name__ == '__main__':
    if '--check' in sys.argv:
        for f in sorted(os.listdir(ZHDIR)):
            n = f[:-5]
            if os.path.exists(os.path.join(EXTRACT, n)):
                cnt, bad = check_encodable(n)
                print(f'{n}: {cnt} 条无法 GBK 编码', bad[:5])
        raise SystemExit
    print('== 注入 ==')
    inject()
    print('== 打包 ==')
    repack_all()