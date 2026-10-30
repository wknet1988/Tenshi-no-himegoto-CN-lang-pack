"""Find which patch triggers the LoadLayer error dialog."""
import sys, os, ctypes, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import launch_cn as L

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
EW = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
GAME = os.path.join(ROOT, 'cn')


def dialogs():
    found = []

    def cb(hw, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(hw, c, 100)
        if c.value == '#32770':
            b = ctypes.create_unicode_buffer(300)
            u32.GetWindowTextW(hw, b, 300)
            if b.value == 'error' or b.value == 'warning':
                kids = []

                def kcb(kh, kl):
                    kb = ctypes.create_unicode_buffer(500)
                    u32.GetWindowTextW(kh, kb, 500)
                    if kb.value:
                        kids.append(kb.value)
                    return True
                u32.EnumChildWindows(hw, EW(kcb), None)
                found.append((b.value, kids))
        return True
    u32.EnumWindows(EW(cb), None)
    return found


def run(label, apply_fn, wait=11):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION()
    k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(GAME, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, 4, None,
                      ctypes.c_wchar_p(GAME), ctypes.byref(si), ctypes.byref(pi))
    h = ctypes.wintypes.HANDLE(k32.OpenProcess(0x1F0FFF, False, pi.dwProcessId))
    apply_fn(h, 0x400000)
    k32.ResumeThread(pi.hThread)
    time.sleep(wait)
    d = dialogs()
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    tag = 'ALIVE' if alive else 'EXIT'
    detail = ''
    for title, kids in d:
        if kids:
            detail = kids[-1][:70]
    print('%-22s %-5s %s' % (label, tag, detail))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.6)


def none(h, b):
    pass


def sites(h, b):
    for r in L.PATCH_SITES:
        L.write_bytes(h, b + r, L.PATCH_BYTES)


def globals_(h, b):
    L.force_codepage(h)


def charset(h, b):
    L.apply_charset_patch(h, b)


def dbcs(h, b):
    L.apply_dbcs_table_patch(h, b)


def title(h, b):
    L.apply_title_patch(h, b)


if __name__ == '__main__':
    run('none', none)
    run('sites', sites)
    run('globals', globals_)
    run('charset', charset)
    run('dbcs', dbcs)
    run('title', title)
