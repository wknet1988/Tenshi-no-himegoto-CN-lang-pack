"""A/B test: which patch group causes the LoadLayer error."""
import sys, os, ctypes, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import launch_cn as L

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
GAME = os.path.join(ROOT, 'cn')


def error_text():
    """Read the error dialog; the mojibake decodes back to Shift-JIS."""
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
                    if kb.value:
                        kids.append(kb.value)
                    return True
                u32.EnumChildWindows(hw, EW(kcb), None)
                for t in kids:
                    if t != '确定':
                        out.append(t)
        return True
    u32.EnumWindows(EW(cb), None)
    return out


def decode_mojibake(s):
    try:
        return s.encode('gbk').decode('cp932')
    except Exception:
        return s


def run(label, do_sites, do_globals, do_charset, do_title, wait=12):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION()
    k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(GAME, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, 4, None,
                      ctypes.c_wchar_p(GAME), ctypes.byref(si), ctypes.byref(pi))
    h = ctypes.wintypes.HANDLE(k32.OpenProcess(0x1F0FFF, False, pi.dwProcessId))
    b = 0x400000
    if do_sites:
        for r in L.PATCH_SITES:
            L.write_bytes(h, b + r, L.PATCH_BYTES)
    if do_globals == 'cptext':
        L.write_dword(h, L.CP_TEXT, 936)
    elif do_globals == 'cpother':
        L.write_dword(h, L.CP_OTHER, 936)
    elif do_globals == 'cpg':
        L.write_dword(h, L.CP_GLOBAL, 936)
    elif do_globals == 'cpcrt':
        L.write_dword(h, L.CP_CRT, 936)
    elif do_globals is True:
        L.force_codepage(h)
    if do_charset:
        L.apply_charset_patch(h, b)
    if do_title:
        L.apply_title_patch(h, b)
    k32.ResumeThread(pi.hThread)
    time.sleep(wait)
    errs = [decode_mojibake(e) for e in error_text()]
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    print('  %-34s %-5s %s' % (label, 'ALIVE' if alive else 'EXIT', errs))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.6)


if __name__ == '__main__':
    run('nothing (baseline)',         False, False, False, False)
    run('sites only',                 True,  False, False, False)
    run('globals only',               False, True,  False, False)
    run('globals CP_TEXT only',       False, 'cptext', False, False)
    run('globals CP_OTHER only',      False, 'cpother', False, False)
    run('globals CP_GLOBAL only',     False, 'cpg',    False, False)
    run('globals CP_CRT only',        False, 'cpcrt',  False, False)
