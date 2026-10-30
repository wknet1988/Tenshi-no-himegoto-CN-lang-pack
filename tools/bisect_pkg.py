"""Rebuild the package with only some scripts localized, to find what breaks."""
import sys, os, shutil, ctypes, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from lcse_tool import parse_lst, build_lst, x, XOR_SCRIPT
from lcse_script import Script
import launch_cn as L

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tenshi')


def dialogs():
    out = []

    def cb(hw, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(hw, c, 100)
        if c.value == '#32770':
            b = ctypes.create_unicode_buffer(300)
            u32.GetWindowTextW(hw, b, 300)
            if b.value == 'error':
                kids = []

                def kcb(kh, kl):
                    kb = ctypes.create_unicode_buffer(600)
                    u32.GetWindowTextW(kh, kb, 600)
                    if kb.value and kb.value != '确定':
                        kids.append(kb.value)
                    return True
                u32.EnumChildWindows(hw, EW(kcb), None)
                out.extend(kids)
        return True
    u32.EnumWindows(EW(cb), None)
    return out


def unsjis(s):
    try:
        return s.encode('gbk').decode('cp932')
    except Exception:
        return s


def build(dst, scripts):
    """Package that localizes only the named scripts."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for f in os.listdir(SRC):
        if f.startswith('lcsebody') or f == 'Thumbs.db':
            continue
        s = os.path.join(SRC, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst, f))
        elif os.path.isdir(s):
            shutil.copytree(s, os.path.join(dst, s), dirs_exist_ok=True)
    recs = parse_lst(os.path.join(SRC, 'lcsebody.lst'))
    body = open(os.path.join(SRC, 'lcsebody'), 'rb').read()
    out = bytearray()
    new = []
    for r in recs:
        blob = body[r['offset']:r['offset'] + r['size']]
        if r['unk'] == 1 and r['name'] in scripts:
            sc = Script(x(blob, XOR_SCRIPT), encoding='cp932')
            sc.encoding = 'gbk'
            blob = x(sc.serialize(), XOR_SCRIPT)
        new.append(dict(r, offset=len(out), size=len(blob)))
        out += blob
    open(os.path.join(dst, 'lcsebody'), 'wb').write(bytes(out))
    open(os.path.join(dst, 'lcsebody.lst'), 'wb').write(build_lst(new))


def run(dst, label):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION(); k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(dst, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, 0, None,
                      ctypes.c_wchar_p(dst), ctypes.byref(si), ctypes.byref(pi))
    time.sleep(10)
    msgs = [unsjis(m) for m in dialogs()]
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    print('  %-26s %-5s %s' % (label, 'ALIVE' if alive else 'EXIT ', msgs))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.5)


if __name__ == '__main__':
    cases = [
        ('none',       []),
        ('INIT only',  ['INIT']),
        ('LOADATT',    ['_LOADATTITLE']),
        ('OP001',      ['OP001']),
        ('all OP',     ['OP001', 'OP002', 'OP003', 'OP004', 'OP005A', 'OP005B', 'OP006']),
    ]
    for label, scripts in cases:
        d = os.path.join(ROOT, '.work', 'bs_' + label.replace(' ', '_'))
        build(d, set(scripts))
        run(d, label)
