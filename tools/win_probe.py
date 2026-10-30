#!/usr/bin/env python3
"""
win_probe.py — 启动游戏并读取窗口标题/错误对话框内容（绕过编码问题）
  python win_probe.py <dir> [seconds]
"""
import ctypes, ctypes.wintypes as w, subprocess, sys, os, time

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

EnumWindows = u32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
GetWindowTextW = u32.GetWindowTextW
GetClassNameW = u32.GetClassNameW
IsWindowVisible = u32.IsWindowVisible
SendMessageW = u32.SendMessageW
EnumChildWindows = u32.EnumChildWindows

WM_COMMAND = 0x0111
BM_CLICK = 0x00F5


def dump_windows():
    out = []

    def cb(h, l):
        if not IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(512)
        GetWindowTextW(h, buf, 512)
        cls = ctypes.create_unicode_buffer(256)
        GetClassNameW(h, cls, 256)
        title = buf.value
        if title:
            kids = []

            def kcb(kh, kl):
                kb = ctypes.create_unicode_buffer(512)
                GetWindowTextW(kh, kb, 512)
                kc = ctypes.create_unicode_buffer(256)
                GetClassNameW(kh, kc, 256)
                if kb.value:
                    kids.append((kc.value, kb.value))
                return True
            EnumChildWindows(h, EnumWindowsProc(kcb), None)
            out.append({'hwnd': h, 'class': cls.value, 'title': title, 'children': kids})
        return True

    EnumWindows(EnumWindowsProc(cb), None)
    return out


def main():
    d = sys.argv[1]
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    exe = os.path.join(d, 'lcsebody.exe')
    p = subprocess.Popen([exe], cwd=d)
    print(f'launched pid={p.pid}, waiting {secs}s ...', flush=True)
    time.sleep(secs)
    wins = dump_windows()
    for w in wins:
        print(f"[WINDOW] class={w['class']!r} title={w['title']!r}")
        for cls, txt in w['children']:
            print(f"    - {cls}: {txt!r}")
    print('--- clicking buttons on #32770 dialogs ---')
    for w in wins:
        if w['class'] == '#32770':
            for cls, txt in w['children']:
                if 'Button' in cls:
                    print(f'  click {txt!r}')
                    SendMessageW(w['hwnd'], WM_COMMAND, 1, 0)
                    break
    time.sleep(3)
    print('--- after ---')
    for w in dump_windows():
        print(f"[WINDOW] class={w['class']!r} title={w['title']!r}")
        for cls, txt in w['children']:
            print(f"    - {cls}: {txt!r}")
    print('alive:', p.poll() is None, 'exitcode:', p.poll())
    try:
        p.kill()
    except Exception:
        pass


if __name__ == '__main__':
    main()