"""Identify which in-memory patch makes the game crash."""
import sys, os, ctypes, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import launch_cn as L

k32 = ctypes.windll.kernel32
GAME = os.path.join(os.path.dirname(HERE), 'cn')


def run(label, apply_fn, limit=16):
    si = L.STARTUPINFO(); si.cb = ctypes.sizeof(si); si.wShowWindow = 1
    pi = L.PROCESS_INFORMATION()
    k32.CreateProcessW.restype = ctypes.c_bool
    exe = os.path.join(GAME, 'lcsebody.exe')
    if not k32.CreateProcessW(ctypes.c_wchar_p(exe), None, None, None, False,
                              4, None, ctypes.c_wchar_p(GAME),
                              ctypes.byref(si), ctypes.byref(pi)):
        print(label, 'launch failed')
        return
    h = ctypes.wintypes.HANDLE(k32.OpenProcess(0x1F0FFF, False, pi.dwProcessId))
    apply_fn(h, 0x400000)
    k32.ResumeThread(pi.hThread)
    alive = True
    t = 0
    while t < limit:
        time.sleep(4); t += 4
        if k32.WaitForSingleObject(pi.hProcess, 0) != 258:
            alive = False
            break
    print('%-26s %2ds  %s' % (label, t, 'OK' if alive else 'CRASH'))
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    time.sleep(0.5)


def none(h, b):
    pass


def dbcs(h, b):
    L.apply_dbcs_table_patch(h, b)


def charset(h, b):
    L.apply_charset_patch(h, b)


def title(h, b):
    L.apply_title_patch(h, b)


def sites(h, b):
    for r in L.PATCH_SITES:
        L.write_bytes(h, b + r, L.PATCH_BYTES)


def globals_(h, b):
    L.force_codepage(h)


def sweep(h, b):
    L.sweep_codepages(h)


if __name__ == '__main__':
    run('baseline', none)
    run('dbcs table', dbcs)
    run('charset', charset)
    run('title', title)
    run('codepage sites', sites)
    run('globals', globals_)
    run('sweep', sweep)
