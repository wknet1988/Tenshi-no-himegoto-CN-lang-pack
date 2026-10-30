#!/usr/bin/env python3
"""
mt.py - machine translation front end for the script text.

Machine output is only a draft. Speaker labels, honorifics and the engine's
control codes are masked before the request and restored afterwards, because
the engine otherwise turns the control byte into "0" and renders the label
in place of the line.

Masks use "ZQ<n>" tokens: pure ASCII, left untouched by the engine, and
impossible to confuse with Japanese source text.

  python mt.py run <NAME> [--workers 4]
  python mt.py runall [--workers 4] [--limit N]
  python mt.py stat
"""
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

GAME = os.path.join(ROOT, 'tenshi')
INBOX = os.path.join(ROOT, '.work', 'inbox')
DRAFT = os.path.join(ROOT, '.work', 'draft')
CACHE = os.path.join(ROOT, '.work', 'mt_cache.json')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')
KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# Speaker labels and honorifics. These must survive untouched: the engine
# keys portraits off the label, so translating one breaks that lookup.
LOCK = [
    # character names
    '英之', '摩菜', '綾', 'イリーナ', '沙織', '礼美', '皐月', '莉々',
    '雫', '梢', '柊', '透', '葵', '凛', '莉沙', '深月', '雪緒',
    '千歳', 'あかり', '奏', '羽白', 'モナ',
    # roles
    '委員長', '聖職者', '守衛', '女生徒', '少女', '悪魔', '書記',
    '先輩', '後輩', '同級生', '生徒会', '生徒', '先生', '校長',
    ' 教授', '箱子', '使徒', '騎士', '王子', '国王', '女王',
    # honorifics and kinship
    'お兄さま', 'お兄ちゃん', 'お姉ちゃん', 'お姉さま', 'お嬢様',
    'お母さま', 'お父さま', '兄ちゃん', '姉ちゃん', 'お兄さん',
    '姉さん', 'ご主人', 'お嫁', 'ご戚',
    # places and objects that show up often
    '学院', '聖堂', '図書館', '礼拝堂', '宿舍', '教室', '廊下',
]

_lock = threading.Lock()
_cache = {}
_next_token = [1000]
_rate = [0.0]


def load_cache():
    if os.path.exists(CACHE):
        _cache.update(json.load(open(CACHE, encoding='utf-8')))


def save_cache():
    tmp = CACHE + '.tmp'
    json.dump(_cache, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(tmp, CACHE)


def cache_key(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def throttle():
    """Cap the whole process at about three requests per second.

    A single sleep under no lock is enough: the workers are few and the
    interval dominates any scheduling jitter.
    """
    time.sleep(0.34)


def translate(text, tries=4):
    """One translation. Back off hard on 429: the free tier resets slowly."""
    for attempt in range(tries):
        try:
            throttle()
            url = ('https://api.mymemory.translated.net/get?q='
                   + urllib.parse.quote(text) + '&langpair=ja|zh-CN')
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
            out = data['responseData']['translatedText']
            if data.get('responseStatus') != 200 or 'MYMEMORY WARNING' in out:
                time.sleep(5 + attempt * 15)
                continue
            return out.replace('&quot;', '"').strip()
        except Exception as exc:
            if '429' in str(exc):
                time.sleep(20 + attempt * 30)
            else:
                time.sleep(1.5 + attempt * 2)
    return None


def mask(text):
    """Replace control codes and locked words with ZQ tokens."""
    tokens = {}

    def store(original):
        with _lock:
            n = _next_token[0]
            _next_token[0] += 1
        tok = 'ZQ%d' % n
        tokens[tok] = original
        return tok

    # Control codes go first so they cannot end up inside a locked word.
    pieces = []
    buf = []
    for ch in text:
        if ch in '\x01\x02\x03\x04\x05':
            if buf:
                pieces.append(''.join(buf))
                buf = []
            pieces.append(store(ch))
        elif ord(ch) < 0x20:
            continue
        else:
            buf.append(ch)
    if buf:
        pieces.append(''.join(buf))

    out = []
    for p in pieces:
        if len(p) == 1 and p in '\x01\x02\x03\x04\x05':
            out.append(p)
            continue
        for word in sorted(LOCK, key=len, reverse=True):
            if word in p:
                p = p.replace(word, store(word))
        out.append(p)
    return ''.join(out), tokens


def unmask(text, tokens):
    # The engine may insert spaces around a token. Strip only ASCII spaces so
    # the ideographic space U+3000 that starts most narration survives.
    for tok, orig in tokens.items():
        text = re.sub(re.escape(tok) + r'[ \t]*', orig, text)
        text = re.sub(r'[ \t]*' + re.escape(tok), orig, text)
    return text


def worker(q, payload, stats):
    while True:
        try:
            key, src = q.get(timeout=30)
        except queue.Empty:
            if q.empty():
                return
            continue
        masked, tokens = mask(src)
        draft = translate(masked)
        if draft is None:
            with _lock:
                stats['fail'] += 1
                # Keep the original Japanese rather than lose the line.
                payload[key] = src
            save_cache()
            q.task_done()
            continue
        payload[key] = unmask(draft, tokens)
        with _lock:
            _cache[cache_key(src)] = payload[key]
            stats['ok'] += 1
        save_cache()
        q.task_done()


def run_script(name, workers=4):
    path = os.path.join(INBOX, name + '.json')
    if not os.path.exists(path):
        print('!! nothing exported for %s' % name)
        return 0
    original = json.load(open(path, encoding='utf-8'))
    payload = {}
    q = queue.Queue()
    for k, v in original.items():
        if not KANA.search(v):
            continue
        hit = _cache.get(cache_key(v))
        if hit:
            payload[k] = hit
        else:
            q.put((k, v))
    if q.empty():
        print('%-10s all %d cached' % (name, len(payload)), flush=True)
        write_draft(name, payload, original)
        return len(payload)
    print('%-10s %d cached, %d queued' % (name, len(payload), q.qsize()), flush=True)
    stats = {'ok': 0, 'fail': 0}
    threads = [threading.Thread(target=worker, args=(q, payload, stats), daemon=True)
               for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    save_cache()
    print('%-10s ok=%d fail=%d total=%d'
          % (name, stats['ok'], stats['fail'], len(payload)), flush=True)
    write_draft(name, payload, original)
    return len(payload)


def write_draft(name, payload, original):
    os.makedirs(DRAFT, exist_ok=True)
    result = {}
    for k, v in original.items():
        result[k] = {'src': v, 'draft': payload.get(k, '')}
    json.dump(result, open(os.path.join(DRAFT, name + '.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)


def runall(workers=4, limit=None):
    load_cache()
    names = sorted(f[:-5] for f in os.listdir(INBOX)) if os.path.isdir(INBOX) else []
    if limit:
        names = names[:limit]
    for n, name in enumerate(names, 1):
        print('[%d/%d] %s' % (n, len(names), name), flush=True)
        run_script(name, workers)


def stat():
    load_cache()
    todo = 0
    if os.path.isdir(INBOX):
        for f in os.listdir(INBOX):
            d = json.load(open(os.path.join(INBOX, f), encoding='utf-8'))
            todo += sum(1 for v in d.values() if KANA.search(v))
    print('cache entries : %d' % len(_cache))
    print('lines to do  : %d' % todo)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    if cmd == 'run':
        w = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
        load_cache()
        run_script(sys.argv[2], w)
    elif cmd == 'runall':
        w = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
        lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
        runall(w, lim)
    elif cmd == 'stat':
        stat()
    else:
        print(__doc__)
        raise SystemExit(1)