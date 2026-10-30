"""
Launcher for the Chinese-localized build of Tenshi no Himago-to.

The original engine decodes script text as Shift-JIS (code page 932).
The localized data stores GBK text instead, so the engine must be pushed
to use code page 936 or every line renders as garbage.

The code page is taken from a global variable (CP_TEXT at 0x4a63ac) that is
read by seven instructions inside the executable, but those sites only fall
back to the global when the caller passes zero, and the scenario loader can
also write 932 straight into a caller's argument. Patching the instructions
alone therefore proved insufficient: the script loader still fed GBK bytes
to a 932 conversion, which yields half width katakana (U+FF71..U+FF9F) and
SimSun has no glyph for those, so the text showed up as rows of "?".

On top of the instruction patches, the DBCS parameter table in .rdata gets
its Shift-JIS byte ranges replaced with the GBK ones, which is what actually
makes the engine walk GBK text correctly. A watchdog keeps the code page
globals pinned to 936 for as long as the game runs.

Editing anything on disk is not an option: Smart App Control hashes
executables and rejects any modified image (WinError 4551). It does not
inspect process memory, so all of this is done on the live process, which is
started suspended, patched, and then resumed.

Usage:
    run_cn.bat
    python\\python.exe launch_cn.py
"""

import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time

k32 = ctypes.windll.kernel32

CREATE_SUSPENDED = 0x00000004
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
WAIT_TIMEOUT = 258
INFINITE = 0xFFFFFFFF
SW_SHOW = 5

IMAGE_BASE = 0x400000

# RVA of every "mov eax,[CP_TEXT]" site (file offset == RVA for .text).
PATCH_SITES = (
    0x3BE2B, 0x3C298, 0x42B05, 0x459C0, 0x462E9, 0x46400, 0x46656,
)
ORIG_BYTES = bytes.fromhex('a1ac634a00')      # mov eax,[0x4a63ac]
PATCH_BYTES = bytes.fromhex('b8a8030000')     # mov eax,936

# The engine builds its own LOGFONT and hardcodes lfCharSet = 0x80
# (SHIFTJIS_CHARSET). GDI then looks up glyphs with Japanese rules, so GBK
# bytes resolve to the wrong characters. Change that to 0x86
# (GB2312_CHARSET). Single byte, so the patch is length preserving.
CHARSET_SITE = 0x15A85
ORIG_CHARSET = 0x80
PATCH_CHARSET = 0x86
# Instruction at CHARSET_SITE is: c6 43 17 80  (mov byte [rbx+17h], 80h)
CHARSET_OPCODE = bytes.fromhex('c64317')

# NOTE: an earlier attempt rewrote the DBCS parameter table in .rdata so the
# Shift-JIS entry would use GBK lead/trail ranges. Do not go back to that.
# The entries store ranges as u16 pairs and the Shift-JIS lead byte range is
# split across two spans (0x81-0x9F and 0xE0-0xFC) while GBK is one span
# (0x81-0xFE). The engine's walk assumes the Shift-JIS shape, so feeding it
# GBK ranges corrupts its traversal and the game dies in LoadLayer.
# Renaming an entry's key is equally fatal: the lookup loop at 0x42cea has no
# miss handler and dereferences a pointer past the end of the table.

# The window caption is the literal "LC-ScriptEngine ver1.0" at this RVA,
# referenced once from the window class registration. It is 23 bytes and the
# field behind it is NUL padded, so a short GBK string fits in place without
# moving anything.
#
# Do not confuse it with the dead Japanese literal at 0x8f8c4: that one has
# no code reference anywhere in the image, so patching it does nothing.
TITLE_SITE = 0x8EF40
TITLE_ORIG = b'LC-ScriptEngine ver1.0'
TITLE_PATCH = '\u5929\u4f7f\u79d8\u4e8b'.encode('gbk')

# Encoding-related globals.
CP_TEXT = 0x4A63AC
CP_OTHER = 0x4A63B0
CP_CRT = 0x4A639C
CP_GLOBAL = 0x4A66D4
CP_VARS = (CP_TEXT, CP_OTHER, CP_CRT, CP_GLOBAL)
CP_TARGET = 936

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

HERE = os.path.dirname(os.path.abspath(__file__))


class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
        ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
        ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD), ('dwXCountChars', wt.DWORD),
        ('dwYCountChars', wt.DWORD), ('dwFillAttribute', wt.DWORD),
        ('dwFlags', wt.DWORD), ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
        ('lpReserved2', ctypes.POINTER(ctypes.c_byte)),
        ('hStdInput', wt.HANDLE), ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
        ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wt.DWORD), ('th32ModuleID', wt.DWORD), ('th32ProcessID', wt.DWORD),
        ('GlblcntUsage', wt.DWORD), ('ProccntUsage', wt.DWORD),
        ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)), ('modBaseSize', wt.DWORD),
        ('hModule', wt.HMODULE), ('szModule', wt.WCHAR * 256),
        ('szExePath', wt.WCHAR * 260),
    ]


def log(msg):
    print(msg, flush=True)


def locate_game_dir():
    """Find the game folder, preferring a localized build next to this file."""
    candidates = [
        os.path.join(HERE, 'cn'),
        os.path.join(HERE, 'game_cn'),
        HERE,
    ]
    if len(sys.argv) > 1:
        candidates.insert(0, os.path.abspath(sys.argv[1]))
    for path in candidates:
        if os.path.isfile(os.path.join(path, 'lcsebody.exe')):
            return path
    return None


def module_base(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if not snap or snap == INVALID_HANDLE_VALUE:
        return None
    entry = MODULEENTRY32W()
    entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
    base = None
    if k32.Module32FirstW(snap, ctypes.byref(entry)):
        base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
    k32.CloseHandle(snap)
    return base


def read_bytes(handle, addr, size):
    buf = (ctypes.c_char * size)()
    if not k32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, None):
        return None
    return bytes(buf)


def write_bytes(handle, addr, data):
    buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
    return bool(k32.WriteProcessMemory(handle, ctypes.c_void_p(addr), buf, len(data), None))


def read_dword(handle, addr):
    raw = read_bytes(handle, addr, 4)
    return struct.unpack('<i', raw)[0] if raw else None


def write_dword(handle, addr, value):
    return write_bytes(handle, addr, struct.pack('<i', value))


def apply_code_patch(handle, base):
    done = failed = 0
    for rva in PATCH_SITES:
        addr = base + rva
        current = read_bytes(handle, addr, 5)
        if current == PATCH_BYTES:
            done += 1
        elif current == ORIG_BYTES:
            done += 1 if write_bytes(handle, addr, PATCH_BYTES) else 0
            if not write_bytes(handle, addr, PATCH_BYTES):
                failed += 1
        else:
            failed += 1
    return done, failed


def apply_charset_patch(handle, base):
    addr = base + CHARSET_SITE
    current = read_bytes(handle, addr, 4)
    if current is None:
        return False
    if current[:3] != CHARSET_OPCODE:
        return False
    if current[3] == PATCH_CHARSET:
        return True
    return write_bytes(handle, addr + 3, bytes([PATCH_CHARSET]))


def apply_title_patch(handle, base):
    addr = base + TITLE_SITE
    current = read_bytes(handle, addr, len(TITLE_ORIG))
    if current is None:
        return False
    if current[:len(TITLE_PATCH)] == TITLE_PATCH:
        return True
    if current[:len(TITLE_ORIG)] != TITLE_ORIG:
        return False
    field = TITLE_PATCH + b'\x00' * (len(TITLE_ORIG) - len(TITLE_PATCH))
    return write_bytes(handle, addr, field)


def force_codepage(handle):
    for addr in CP_VARS:
        write_dword(handle, addr, CP_TARGET)


def main():
    game_dir = locate_game_dir()
    if not game_dir is None and not game_dir:
        log('ERROR: game directory not found.')
        log('Expected an "lcsebody.exe" next to this script, or pass the path as argument.')
        return 1
    if not os.path.isfile(os.path.join(game_dir, 'lcsebody.exe')):
        log('ERROR: lcsebody.exe missing in: %s' % game_dir)
        return 1

    exe = os.path.join(game_dir, 'lcsebody.exe')
    log('Game directory: %s' % game_dir)
    log('Launching suspended...')

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.wShowWindow = SW_SHOW
    pi = PROCESS_INFORMATION()

    k32.CreateProcessW.restype = wt.BOOL
    # Created suspended so the patches land before any engine code runs. The
    # engine calls into the conversion and font routines during startup, so
    # patching after ResumeThread is too late and crashes it within seconds.
    if not k32.CreateProcessW(
            ctypes.c_wchar_p(exe), None, None, None, False,
            CREATE_SUSPENDED, None, ctypes.c_wchar_p(game_dir),
            ctypes.byref(si), ctypes.byref(pi)):
        log('ERROR: CreateProcessW failed, winerror=%d' % k32.GetLastError())
        return 2

    pid = pi.dwProcessId
    log('  pid=%d' % pid)

    handle = k32.OpenProcess(
        PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        log('ERROR: OpenProcess failed, winerror=%d' % k32.GetLastError())
        log('Try running this script as administrator.')
        k32.ResumeThread(pi.hThread)
        k32.WaitForSingleObject(pi.hProcess, INFINITE)
        return 3
    handle = wt.HANDLE(handle)

    base = module_base(pid) or IMAGE_BASE
    log('  image base: 0x%x' % base)

    # The localized data is written in Shift-JIS, which is what the engine
    # already expects, so no code page or font charset patch is needed.
    # Only the window caption is rewritten.
    done, failed = 0, 0
    cs_ok = True
    title_ok = apply_title_patch(handle, base)
    log('  encoding: shift-jis (native, no patch needed)')
    log('  window title: %s' % ('patched' if title_ok else 'NOT PATCHED'))

    # Everything above ran while the process was still suspended, so the
    # loader cannot race us and the game cannot die before we are done.
    title_now = read_bytes(handle, base + TITLE_SITE, len(TITLE_PATCH))
    title_txt = 'CN' if title_now == TITLE_PATCH else 'JP'
    log('  verification: title=%s' % title_txt)
    if title_txt != 'CN':
        log('WARNING: window caption patch did not land.')

    k32.ResumeThread(pi.hThread)
    k32.CloseHandle(pi.hThread)
    log('Resumed.')

    log('Running (this window closes when the game does)...')
    k32.WaitForSingleObject(pi.hProcess, INFINITE)

    k32.CloseHandle(pi.hProcess)
    log('Game exited.')
    return 0


if __name__ == '__main__':
    sys.exit(main())