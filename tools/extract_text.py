#!/usr/bin/env python3
"""
extract_text.py — 从脚本中提取可翻译文本，生成翻译清单 JSON
  python extract_text.py extract <脚本...> -o tasks.json
  python extract_text.py apply <tasks.json> --trans zh.json
"""
import sys, os, json, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcse_script import load

# UI / 系统脚本
UI_SCRIPTS = ['__MAINSTREAM', '_CREDIT', '_LOADATTITLE', '_LOADATSAV01', '_LOADATSAV02',
              '_MSGBOXMAIN_OFF', '_MSGBOXMAIN_ON', '_TITLE']

# 判定为「需要翻译」的文本：含对话标记或含假名/汉字
KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
CTRL = re.compile(r'[\x00-\x08\x0b-\x1f]')


def is_resource(s):
    """资源名 / 素材名，不翻译"""
    t = s.strip('\x00').strip()
    if not t:
        return True
    return bool(re.fullmatch(r'[A-Za-z0-9_\-\.\\/]+', t))


def classify(s):
    """返回 (类型, 说话人, 正文)"""
    t = s.rstrip('\x00')
    # 形如 "名前\x01台词\x02\x03"
    m = re.match(r'^([^\x00-\x1f]*?)\x01(.*)$', t, re.S)
    if m:
        name = m.group(1)
        rest = m.group(2)
        if name and KANA.search(name):
            return 'dialog', name, rest
        return 'narr', None, rest
    if t.startswith('\x01'):
        return 'narr', None, t
    return 'other', None, t


def collect(paths):
    items = []
    for p in paths:
        name = os.path.basename(p)
        try:
            sc = load(p)
        except Exception as e:
            print(f'  skip {name}: {e}')
            continue
        refs = sc.push_refs()
        if not refs:
            continue
        for si in sorted(set(i for _, i in refs)):
            s = sc.strings[si]
            if is_resource(s):
                continue
            kind, speaker, body = classify(s)
            items.append({'file': name, 'idx': si, 'kind': kind,
                          'speaker': speaker, 'src': s})
    return items


def cmd_extract(argv):
    out = None
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == '-o':
            out = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    items = collect(files)
    json.dump(items, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(items)} 条 -> {out}')
    from collections import Counter
    print(Counter(x['kind'] for x in items))


def cmd_apply(argv):
    tasks = json.load(open(argv[2], encoding='utf-8'))
    trans = json.load(open(argv[4], encoding='utf-8')) if len(argv) > 4 else {}
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.work', 'extract')
    byfile = {}
    for t in tasks:
        key = f"{t['file']}#{t['idx']}"
        if key in trans:
            byfile.setdefault(t['file'], {})[t['idx']] = trans[key]
    n = 0
    for fname, mapping in byfile.items():
        p = os.path.join(root, fname)
        sc = load(p, encoding='gbk' if False else 'cp932')
        sc.set_strings(mapping)
        sc.save = None
        open(p, 'wb').write(sc.serialize())
        n += len(mapping)
        print(f'  {fname}: {len(mapping)} 条')
    print(f'共写入 {n} 条')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'extract':
        cmd_extract(sys.argv[2:])
    elif cmd == 'apply':
        cmd_apply(sys.argv[2:])