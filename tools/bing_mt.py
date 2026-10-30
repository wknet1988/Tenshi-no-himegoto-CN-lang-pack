#!/usr/bin/env python3
"""
bing_mt.py -- translation engine for the script text, backed by the Bing
web translator.

The public endpoint wants a per-session token, so the token is scraped once
from the translator page and then refreshed when a request is rejected. Text
is sent in batches of a few hundred characters, which is what makes this
usable for twenty thousand lines.

  python bing_mt.py test
  python bing_mt.py run <NAME> [--workers 3]
  python bing_mt.py runall [--workers 3] [--limit N]
  python bing_mt.py stat
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

INBOX = os.path.join(ROOT, '.work', 'inbox')
DRAFT = os.path.join(ROOT, '.work', 'draft')
CACHE = os.path.join(ROOT, '.work', 'bing_cache.json')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edge/120.0')
KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# Speaker labels, honorifics and set nouns. The engine turns 摩菜 into
# "Mona vegetables" and 英之 into "Hideyuki", so they are masked first.
LOCK = [
    '英之', '摩菜', '綾', 'イリーナ', '沙織', '礼美', '皐月', '莉々',
    '雫', '梢', '柊', '透', '葵', '凛', '莉沙', '深月', '雪緒',
    '千歳', 'あかり', '奏', '羽白', 'モナ', '委員長', '聖職者',
    '守衛', '女生徒', '少女', '悪魔', '書記', '先輩', '後輩',
    '同級生', '生徒会', '生徒', '先生', '校長', '騎士', '王子',
    '国王', '女王', '使徒', '学院', '聖堂', '図書館', '礼拝堂',
    '宿舍', '教室', '廊下', 'お兄さま', 'お兄ちゃん', 'お姉ちゃん',
    'お姉さま', 'お嬢様', 'お母さま', 'お父さま', '兄ちゃん', '姉ちゃん',
]

_state = {'token': None, 'ig': None, 'iid': 'translator.5023', 'at': 0.0}
_lock = threading.Lock()
_cache = {}
_tok = [1000]


def load_cache():
    if os.path.exists(CACHE):
        _cache.update(json.load(open(CACHE, encoding='utf-8')))


def save_cache():
    tmp = CACHE + '.tmp'
    json.dump(_cache, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
    os.replace(tmp, CACHE)


def key(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def fetch_token():
    """Scrape a fresh session token and the page's IG value."""
    req = urllib.request.Request('https://cn.bing.com/translator',
                                 headers={'User-Agent': UA})
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')
    m = re.search(r'params_AbusePreventionHelper\s*=\s*\[(\d+),\s*"([^"]+)"', html)
    if not m:
        return None, None
    ig = re.search(r'IG:"([^"]+)"', html)
    # The endpoint rejects an IID that does not match the page.
    iid = re.search(r'data-iid="([^"]+)"', html)
    return m.group(2), (ig.group(1) if ig else None), (iid.group(1) if iid else None)


def refresh():
    tok, ig, iid = fetch_token()
    if tok:
        _state['token'] = tok
        _state['ig'] = ig
        _state['iid'] = iid


def ensure_token():
    with _lock:
        if not _state['token']:
            refresh()
    return _state['token']


def mask(text):
    tokens = {}

    def store(original):
        with _lock:
            n = _tok[0]
            _tok[0] += 1
        t = 'ZQ%d' % n
        tokens[t] = original
        return t

    pieces, buf = [], []
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
        for w in sorted(LOCK, key=len, reverse=True):
            if w in p:
                p = p.replace(w, store(w))
        out.append(p)
    return ''.join(out), tokens


def unmask(text, tokens):
    for t, orig in tokens.items():
        text = re.sub(re.escape(t) + r'[ \t]*', orig, text)
        text = re.sub(r'[ \t]*' + re.escape(t), orig, text)
    return text


def post_once(text, tries=3):
    """One request. Returns translated text or None."""
    url = ('https://www.bing.com/ttranslatev3?isVertical=1&IG='
           + (_state['ig'] or '')
           + '&IID=' + (_state.get('iid') or 'translator.5023'))
    body = [
        'fromLang=ja', 'to=zh-Hans', 'text=' + urllib.parse.quote(text),
        'tryFetchingGenderDebiasedTranslations=true',
        'token=' + urllib.parse.quote(_state['token'] or ''),
    ]
    data = '&'.join(body).encode()
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': UA,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.bing.com/translator',
    })
    raw = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
    d = json.loads(raw)
    if d.get('statusCode') not in (200, None) or not d.get('translations'):
        return None
    return d['translations'][0].get('text', '')


def post(text):
    ensure_token()
    for attempt in range(3):
        try:
            out = post_once(text)
            if out:
                return out
        except Exception:
            pass
        # Token is the usual culprit; refresh and retry once.
        time.sleep(0.4)
        with _lock:
            refresh()
        time.sleep(0.6 + attempt)
    return None


def worker(q, payload, stats, name):
    while True:
        try:
            k, src = q.get(timeout=20)
        except queue.Empty:
            if q.empty():
                return
            continue
        masked, tokens = mask(src)
        out = post(masked)
        if out is None:
            with _lock:
                stats['fail'] += 1
                payload[k] = src          # keep Japanese rather than lose it
            save_cache()
            q.task_done()
            continue
        payload[k] = unmask(out, tokens)
        with _lock:
            _cache[key(src)] = payload[k]
            stats['ok'] += 1
        save_cache()
        q.task_done()


def run_script(name, workers=3):
    path = os.path.join(INBOX, name + '.json')
    if not os.path.exists(path):
        print('!! nothing exported for %s' % name)
        return 0
    original = json.load(open(path, encoding='utf-8'))
    payload, q = {}, queue.Queue()
    for k, v in original.items():
        if not KANA.search(v):
            continue
        hit = _cache.get(key(v))
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
    ths = [threading.Thread(target=worker, args=(q, payload, stats, name), daemon=True)
           for _ in range(workers)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    save_cache()
    print('%-10s ok=%d fail=%d total=%d'
          % (name, stats['ok'], stats['fail'], len(payload)), flush=True)
    write_draft(name, payload, original)
    return len(payload)


def write_draft(name, payload, original):
    os.makedirs(DRAFT, exist_ok=True)
    result = {k: {'src': v, 'draft': payload.get(k, '')} for k, v in original.items()}
    json.dump(result, open(os.path.join(DRAFT, name + '.json'), 'w',
                           encoding='utf-8'), ensure_ascii=False, indent=1)


def test():
    ensure_token()
    print('token:', (_state['token'] or '')[:20], 'IG:', _state['ig'])
    for s in ['目を閉じて気持ちを落ち着けるんだ',
              '摩菜\x01「きゃっ、は」\x02\x03',
              '本当に綺麗なんだ']:
        m, t = mask(s)
        out = post(m)
        print('%r -> %r' % (s[:34], unmask(out or '', t)[:44]))


def runall(workers=3, limit=None):
    load_cache()
    names = sorted(f[:-5] for f in os.listdir(INBOX)) if os.path.isdir(INBOX) else []
    if limit:
        names = names[:limit]
    for n, name in enumerate(names, 1):
        print('[%d/%d] %s' % (n, len(names), name), flush=True)
        run_script(name, workers)


def stat():
    load_cache()
    print('cache entries: %d' % len(_cache))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    c = sys.argv[1]
    if c == 'test':
        test()
    elif c == 'run':
        w = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 3
        load_cache()
        run_script(sys.argv[2], w)
    elif c == 'runall':
        w = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 3
        lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
        runall(w, lim)
    elif c == 'stat':
        stat()
    else:
        print(__doc__)
        raise SystemExit(1)