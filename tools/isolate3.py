"""Compare patching while suspended vs after resume."""
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
    out = []

    def cb(hw, l):
        c = ctypes.create_unicode_buffer(100)
        u32.GetClassNameW(hw, c, 100)
        if c.value == '#32770':
            b = ctypes.create_unicode_buffer(300)
            u32.GetWindowTextW(hw, b, 300)
            if b.value in ('error', 'warning'):
                kids = []

                def kcb(kh, kl):
                    kb = ctypes.create_unicode_buffer(500)
                    u32.GetWindowTextW(kh, kb, 500)
                    if kb.value:
                        kids.append(kb.value)
                    return True
                u32.EnumChildWindows(hw, EW(kcb), None)
                out.append(kids[-1][:60] if kids else b.value)
        return True
    u32.EnumWindows(EW(cb), None)
    return out


def full_patch(h, b):
    for r in L.PATCH_SITES:
        L.write_bytes(h, b + r, L.PATCH_BYTES)
    L.force_codepage(h)
    L.apply_charset_patch(h, b)
    L.apply_dbcs_table_patch(h, b)
    L.apply_title_patch(h, b)


def launch(suspend, patch_after, wait=14):
    flags = 4 if suspend else 0
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION()
    k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(GAME, 'lcsebody.exe')
    k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False, flags, None,
                      ctypes.c_wchar_p(GAME), ctypes.byref(si), ctypes.byref(pi))
    h = ctypes.wintypes.HANDLE(k32.OpenProcess(0x1F0FFF, False, pi.dwProcessId))
    b = 0x400000
    if patch_after == 'before':
        full_patch(h, b)
        k32.ResumeThread(pi.hThread)
    else:
        k32.ResumeThread(pi.hThread)
        time.sleep(2.0)
        full_patch(h, b)
    time.sleep(wait)
    d = dialogs()
    alive = k32.WaitForSingleObject(pi.hProcess, 0) == 258
    print('  %-26s %-5s %s' % ('suspend=%s patch=%s' % (bool(suspend), patch_after),
                                'ALIVE' if alive else 'EXIT', d))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.6)


if __name__ == '__main__':
    for i in range(2):
        print('round', i + 1)
        launch(True, 'before')
        launch(False, 'after')
