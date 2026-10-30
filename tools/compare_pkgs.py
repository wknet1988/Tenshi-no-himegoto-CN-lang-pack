"""Compare original vs localized data packages, several runs each."""
import sys, os, ctypes, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import launch_cn as L

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))


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
    """Mojibake in the dialog is Shift-JIS bytes shown as GBK; put it back."""
    try:
        return s.encode('gbk').decode('cp932')
    except Exception:
        return s


def once(gdir):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION()
    k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(gdir, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, 0, None,
                      ctypes.c_wchar_p(gdir), ctypes.byref(si), ctypes.byref(pi))
    time.sleep(10)
    msgs = [unsjis(m) for m in dialogs()]
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.6)
    return alive, msgs


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dirs = [os.path.join(root, '.work', 'vanilla'), os.path.join(root, 'cn')]
    for d in dirs:
        print(os.path.basename(d))
        for i in range(4):
            alive, msgs = once(d)
            tag = 'ALIVE' if alive else 'EXIT '
            print('  run%d %s %s' % (i + 1, tag, msgs))
