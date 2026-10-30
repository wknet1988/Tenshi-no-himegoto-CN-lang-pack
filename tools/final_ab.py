"""Toggle each patch group on its own so the user can identify the culprit."""
import sys, os, ctypes, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import launch_cn as L

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
GAME = os.path.join(ROOT, 'cn')


def dialogs(pid):
    """Only report dialogs owned by this pid."""
    out = []

    def cb(hw, l):
        wpid = ctypes.c_uint32()
        u32.GetWindowThreadProcessId(hw, ctypes.byref(wpid))
        if wpid.value != pid:
            return True
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


def once(label, sites, charset, title, globals_):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION(); k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(GAME, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, 4, None,
                      ctypes.c_wchar_p(GAME), ctypes.byref(si), ctypes.byref(pi))
    h = ctypes.wintypes.HANDLE(k32.OpenProcess(0x1F0FFF, False, pi.dwProcessId))
    b = 0x400000
    if sites:
        for r in L.PATCH_SITES:
            L.write_bytes(h, b + r, L.PATCH_BYTES)
    if charset:
        L.apply_charset_patch(h, b)
    if title:
        L.apply_title_patch(h, b)
    if globals_:
        L.force_codepage(h)
    k32.ResumeThread(pi.hThread)
    time.sleep(10)
    msgs = [unsjis(m) for m in dialogs(pi.dwProcessId)]
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    print('  %-30s %-5s %s' % (label, 'ALIVE' if alive else 'EXIT ', msgs))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.5)


if __name__ == '__main__':
    import sys as _s
    mode = _s.argv[1] if len(_s.argv) > 1 else 'all'
    for i in range(3):
        if mode == 'all':
            once('all patches',      True,  True,  True,  True)
        elif mode == 'notitle':
            once('sites+charset',    True,  True,  False, True)
        elif mode == 'nosites':
            once('charset+title',    False, True,  True,  True)
        else:
            once('nothing',          False, False, False, False)
