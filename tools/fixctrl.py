"""Rebuild translated lines around the engine's control-code frame.

A source line looks like:

    英之 \x01 「oggle body 」 \x02\x03
    ^label  ^open   ^body      ^close

The label is the speaker name; the engine resolves the portrait from it, so
it must be carried over byte for byte. Only the body is translated.

The rebuild is idempotent: running it twice gives the same result, because it
always works from the *source* frame and the *translated* body, and the body
is recovered by dropping anything that looks like framing.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZHDIR = os.path.join(ROOT, '.work', 'zh')
INBOX = os.path.join(ROOT, '.work', 'inbox')

CTRL = '\x01\x02\x03\x04\x05'
LEAD_MARK = '\u3000'          # ideographic space starts narration


def signature(text):
    return [c for c in text if c in CTRL]


def frame(orig):
    """Return (prefix, body, suffix) for a source line."""
    i = orig.find('\x01')
    if i < 0:
        return '', orig, ''
    prefix = orig[:i + 1]
    rest = orig[i + 1:]
    suffix = ''
    while rest and rest[-1] in '\x02\x03\x05':
        suffix = rest[-1] + suffix
        rest = rest[:-1]
    return prefix, rest, suffix


def strip_frame(text):
    """Recover the translated body: drop control bytes and any repeated label.

    The label is stripped because fixctrl may be run more than once over a
    file that still carries a previous frame.
    """
    return ''.join(c for c in text if c not in CTRL)


def drop_label(body, label):
    """Remove a leading copy of the speaker label from a body."""
    lab = label.split('\x01')[0].strip(' \t\u3000')
    if not lab:
        return body
    out = body
    while True:
        s = out.lstrip(' \t\u3000')
        if s.startswith(lab):
            s = s[len(lab):]
            out = s
            continue
        out = s
        break
    return out


def repair(name, verbose=True):
    src_path = os.path.join(INBOX, name + '.json')
    zh_path = os.path.join(ZHDIR, name + '.json')
    if not (os.path.exists(src_path) and os.path.exists(zh_path)):
        return 0
    src = json.load(open(src_path, encoding='utf-8'))
    zh = json.load(open(zh_path, encoding='utf-8'))
    fixed = 0
    for k, text in list(zh.items()):
        orig = src.get(k)
        if orig is None:
            continue
        prefix, _sbody, suffix = frame(orig)
        body = drop_label(strip_frame(text), prefix)
        body = body.strip(' \t\r\n')
        new = prefix + body + suffix
        if new != text:
            zh[k] = new
            fixed += 1
    if fixed:
        json.dump(zh, open(zh_path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    if verbose:
        print('%-10s repaired %d' % (name, fixed))
    return fixed


def verify(name):
    src = json.load(open(os.path.join(INBOX, name + '.json'), encoding='utf-8'))
    zh = json.load(open(os.path.join(ZHDIR, name + '.json'), encoding='utf-8'))
    bad = 0
    for k, text in zh.items():
        orig = src.get(k)
        if orig is None:
            continue
        if signature(orig) != signature(text):
            print('   ctrl  %s: %r vs %r' % (k, signature(orig), signature(text)))
            bad += 1
        ol = orig.split('\x01')[0]
        nl = text.split('\x01')[0]
        if ol != nl:
            print('   label %s: %r -> %r' % (k, ol, nl))
            bad += 1
    print('%-10s %d lines, %d problems' % (name, len(zh), bad))
    return bad


if __name__ == '__main__':
    mode = sys.argv[1] if sys.argv[1:] else 'repair'
    args = sys.argv[2:] if mode == 'verify' else sys.argv[1:]
    names = args or sorted(f[:-5] for f in os.listdir(ZHDIR))
    if mode == 'verify':
        print('total problems: %d' % sum(verify(n) for n in names))
    else:
        for n in names:
            repair(n)
        print('total problems: %d' % sum(verify(n) for n in names))
