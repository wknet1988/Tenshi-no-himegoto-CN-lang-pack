#!/usr/bin/env python3
"""Trace the engine's font creation and glyph calls inside the running game."""
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32

CREATE_SUSPENDED = 0x00000004
ACCESS = 0x0010 | 0x0020 | 0x0008 | 0x0400

PATCH_SITES = (0x3BE2B, 0x3C298, 0x42B05, 0x459C0, 0x462E9, 0x46400, 0x46656)
ORIG = bytes.fromhex('a1ac634a00')
PATCHED = bytes.fromhex('b8a8030000')
CP_VARS = (0x4A63AC, 0x4A63B0, 0x4A66D4)

LOGFONT_SIZE = 0x44


class SI(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR),
                ('lpTitle', wt.LPWSTR), ('dwX', wt.DWORD), ('dwY', wt.DWORD),
                ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD), ('dwXCountChars', wt.DWORD),
                ('dwYCountChars', wt.DWORD), ('dwFillAttribute', wt.DWORD),
                ('dwFlags', wt.DWORD), ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
                ('lpReserved2', ctypes.POINTER(ctypes.c_byte)),
                ('hStdInput', wt.HANDLE), ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
                ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


def rb(h, a, n):
    b = (ctypes.c_char * n)()
    return bytes(b) if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, None) else None


def wb(h, a, d):
    b = (ctypes.c_char * len(d)).from_buffer_copy(d)
    return bool(k32.WriteProcessMemory(h, ctypes.c_void_p(a), b, len(d), None))


def main():
    game = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'cn')
    si = SI(); si.cb = ctypes.sizeof(SI); si.wShowWindow = 1
    pi = PI()
    k32.CreateProcessW.restype = wt.BOOL
    ok = k32.CreateProcessW(ctypes.c_wchar_p(os.path.join(game, 'lcsebody.exe')),
                             None, None, None, False, CREATE_SUSPENDED, None,
                             ctypes.c_wchar_p(game), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print('launch failed', k32.GetLastError()); return
    pid = pi.dwProcessId
    h = wt.HANDLE(k32.OpenProcess(ACCESS, False, pid))

    for rva in PATCH_SITES:
        wb(h, 0x400000 + rva, PATCHED)
    for a in CP_VARS:
        wb(h, a, struct.pack('<i', 936))

    # Breakpoint right before CreateFontIndirectA (0x15d4b) so we can read the LOGFONT.
    bp_addr = 0x400000 + 0x15D4B
    bp_orig = rb(h, bp_addr, 1)
    print('byte at 0x15d4b:', bp_orig.hex())
    # INT3
    wb(h, bp_addr, b'\xcc')

    # Also break at the GetGlyphOutlineA call site 0x15c80.
    bp2_addr = 0x400000 + 0x15C80
    bp2_orig = rb(h, bp2_addr, 1)
    wb(h, bp2_addr, b'\xcc')

    k32.ResumeThread(pi.hThread)
    print('running with breakpoints at CreateFontIndirectA + GetGlyphOutlineA')

    TH32CS_SNAPTHREAD = 0x00000004
    hits = {0x15D4B: 0, 0x15C80: 0}
    t0 = time.time()
    while time.time() - t0 < 40:
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        thread = wt.HANDLE(-1)
        tid = 0
        THREADENTRY32 = type('T', (ctypes.Structure,), {
            '_fields_': [('dwSize', wt.DWORD), ('cntUsage', wt.DWORD),
                         ('th32ThreadID', wt.DWORD), ('th32OwnerProcessID', wt.DWORD),
                         ('tpBasePri', wt.LONG), ('tpDeltaPri', wt.LONG),
                         ('dwFlags', wt.DWORD)]})
        te = THREADENTRY32(); te.dwSize = ctypes.sizeof(THREADENTRY32)
        if k32.Thread32First(snap, ctypes.byref(te)):
            while True:
                if te.th32OwnerProcessID == pid:
                    tid = te.th32ThreadID; thread = wt.HANDLE(-1)
                    break
                if not k32.Thread32Next(snap, ctypes.byref(te)):
                    break
        k32.CloseHandle(snap)
        if not tid:
            time.sleep(0.05); continue
        th = wt.HANDLE(k32.OpenThread(0x001F0FFF, False, tid))
        if not th:
            time.sleep(0.05); continue
        # Give it a chance to hit the breakpoint
        time.sleep(0.12)
        ctxbuf = (ctypes.c_byte * 716)()
        ctypes.memmove(ctxbuf, ctypes.create_string_buffer(b'x' * 716), 716)
        CONTEXT = type('C', (ctypes.Structure,), {
            '_fields_': [('dwFlags', wt.DWORD), ('dr0', wt.DWORD), ('dr1', wt.DWORD),
                         ('dr2', wt.DWORD), ('dr3', wt.DWORD), ('dr6', wt.DWORD),
                         ('dr7', wt.DWORD)] + [('f' + str(i).zfill(2), wt.DWORD) for i in range(8)] +
                         [('g' + str(i).zfill(2), wt.DWORD) for i in range(8)] +
                         [('r' + str(i).zfill(2), wt.DWORD) for i in range(16)] +
                         [('segi', wt.DWORD)] + [('flt', wt.DWORD) for _ in range(20)] +
                         [('seg', wt.DWORD)] + [('e', ctypes.c_uint64)] + [('fpp', wt.DWORD)] +
                         [('sys', wt.DWORD)] +
                         [('t', wt.DWORD), ('pad0', wt.DWORD), ('pad1', wt.DWORD), ('pad2', wt.DWORD)] +
                         [('mxcsr', wt.DWORD)] +
                         [('segcs', wt.DWORD), ('segds', wt.DWORD), ('segss', wt.DWORD),
                          ('segfs', wt.DWORD), ('seggs', wt.DWORD)] +
                         [('w', wt.DWORD)] + [('mx', ctypes.c_ushort)] +
                         [('csr', ctypes.c_ushort), ('ds', ctypes.c_ushort),
                          ('es', ctypes.c_ushort), ('fs', ctypes.c_ushort),
                          ('gs', ctypes.c_ushort), ('ss', ctypes.c_ushort)] +
                         [('edi', wt.DWORD), ('esi', wt.DWORD), ('ebx', wt.DWORD),
                          ('edx', wt.DWORD), ('ecx', wt.DWORD), ('eax', wt.DWORD),
                          ('ebp', wt.DWORD), ('eip', wt.DWORD),
                          ('cs', wt.DWORD), ('eflags', wt.DWORD),
                          ('esp', wt.DWORD), ('ss', wt.DWORD)]})
        ctx = CONTEXT()
        ctx.ContextFlags = 0x10001F  # CONTEXT_CONTROL | CONTEXT_INTEGER
        if k32.GetThreadContext(th, ctypes.byref(ctx)):
            if ctx.eip in (bp_addr, bp_addr + 1):
                hits[0x15D4B] += 1
                if hits[0x15D4B] == 1:
                    print('\n=== CreateFontIndirectA hit ===')
                    print('  EIP=%#x  ESP=%#x' % (ctx.eip, ctx.esp))
                    # stdcall: last arg at [esp+4] = plogfont
                    sp = rb(h, ctx.esp, 16)
                    if sp:
                        ptr = struct.unpack('<I', sp[4:8])[0]
                        lf = rb(h, ptr, LOGFONT_SIZE)
                        if lf:
                            print('  LOGFONT @%#x' % ptr)
                            print('    lfHeight=%d lfWidth=%d lfEscapement=%d lfWeight=%d' % (
                                struct.unpack('<i', lf[0:4])[0], struct.unpack('<i', lf[4:8])[0],
                                struct.unpack('<i', lf[8:12])[0], struct.unpack('<i', lf[16:20])[0]))
                            cs = lf[23]
                            print('    lfCharSet=%d  (0=ANSI 1=DEFAULT 128=SHIFTJIS 134=GB2312)' % cs)
                            print('    lfQuality=%d  lfPitchAndFamily=%#x' % (lf[25], lf[27]))
                            name = lf[28:28+32].split(b'\x00')[0]
                            print('    lfFaceName=%r' % name)
                # restore and single-step
                wb(h, bp_addr, bp_orig)
                k32.SetThreadContext(th, ctypes.byref(ctx))
                k32.ResumeThread(th)
        else:
            wb(h, bp_addr, bp_orig)
            if bp2_addr and not bp2_orig:
                pass
        k32.CloseHandle(th)
        time.sleep(0.05)
    print('\nhits:', hits)
    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass


if __name__ == '__main__':
    main()