import sys, os
sys.path.insert(0, 'tools')
from lcse_script import Script
from pipeline import KANA
ch = sys.argv[1]
o = Script(open('.work/extract/%s' % ch, 'rb').read(), encoding='cp932')
work = [i for i, s in enumerate(o.strings) if KANA.search(s)]
for i in work:
    s = o.strings[i]
    has01 = '\x01' in s
    # show raw with control chars
    r = s.replace('\x01','\\x01').replace('\x02','\\x02').replace('\x03','\\x03')
    # decode kana search snippet
    print('%d %s | %s' % (i, 'SPK' if has01 else 'NAR', r[:80]))
