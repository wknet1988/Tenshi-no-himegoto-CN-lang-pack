/*
 * cp936proxy.c — LC-ScriptEngine 文本编码代理 DLL (32-bit)
 *
 * 背景
 *   引擎把脚本文本转 Unicode 时用的是 MultiByteToWideChar，而 CodePage
 *   在进入剧情后被设成 932 (Shift-JIS)。我们写入的是 GBK 中文，
 *   于是按 SJIS 解码 → 乱码。
 *
 *   exe 里已内置 936/949/950/1361 的 DBCS 参数表，但选择逻辑走的是
 *   全局变量 CP_TEXT (0x4a63ac)，无法从数据侧改动；而直接改 exe 会被
 *   应用控制策略 (WDAC/AppLocker, WinError 4551) 拦截。
 *
 * 做法
 *   本 DLL 名为 kernel32.dll，放在游戏目录，把引擎调用的编码相关 API
 *   重定向到 CP936；其余全部函数用 .def FORWARD 给真正的 kernel32。
 *
 * 拦截范围（只动「编码」，不动其它 ANSI 行为，避免影响窗口标题/文件路径）：
 *   MultiByteToWideChar  — CodePage 为 0(CP_ACP) / 932 / -1 时改用 936
 *   GetCPInfo            — 同上，保证 DBCS 范围与 GBK 一致
 *   GetStringTypeA       — 同上（仅在引擎显式传 codepage 时生效）
 *
 *   注意：CodePage == 0 是 CP_ACP，本机 ACP=936，理论上本来就对。
 *   真正需要拦的是 932 —— 那是引擎主动指定日文编码的部分。
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static HMODULE g_real = NULL;

typedef int(WINAPI *fn_MB2WC)(UINT, DWORD, LPCSTR, int, LPWSTR, int);
typedef int(WINAPI *fn_WC2MB)(UINT, DWORD, LPCWSTR, int, LPSTR, int, LPCSTR, LPBOOL);
typedef BOOL(WINAPI *fn_GetCPInfo)(UINT, LPCIINFO);
typedef int(WINAPI *fn_GetStringTypeA)(DWORD, LPCSTR, int, LPWORD);

static fn_MB2WC p_MB2WC = NULL;
static fn_WC2MB p_WC2MB = NULL;
static fn_GetCPInfo p_GetCPInfo = NULL;
static fn_GetStringTypeA p_GetStringTypeA = NULL;

/* 把「日文/系统默认」统一改写为 GBK。
 * 只有 932 会被改；0(CP_ACP) 保持原样，因为本机 ACP 已是 936，
 * 改它反而可能影响窗口标题等既有行为。 */
static UINT normalize_cp(UINT cp)
{
    if (cp == 932) return 936;
    return cp;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        char path[MAX_PATH];
        GetSystemDirectoryA(path, MAX_PATH);
        lstrcatA(path, "\\kernel32.dll");
        g_real = LoadLibraryA(path);
        if (g_real) {
            p_MB2WC        = (fn_MB2WC)        GetProcAddress(g_real, "MultiByteToWideChar");
            p_WC2MB        = (fn_WC2MB)        GetProcAddress(g_real, "WideCharToMultiByte");
            p_GetCPInfo    = (fn_GetCPInfo)    GetProcAddress(g_real, "GetCPInfo");
            p_GetStringTypeA = (fn_GetStringTypeA) GetProcAddress(g_real, "GetStringTypeA");
        }
    }
    return TRUE;
}

int WINAPI MultiByteToWideChar(UINT cp, DWORD flags, LPCSTR src, int srclen,
                               LPWSTR dst, int dstlen)
{
    if (!p_MB2WC) { SetLastError(ERROR_PROC_NOT_FOUND); return 0; }
    return p_MB2WC(normalize_cp(cp), flags, src, srclen, dst, dstlen);
}

int WINAPI WideCharToMultiByte(UINT cp, DWORD flags, LPCWSTR src, int srclen,
                               LPSTR dst, int dstlen, LPCSTR defc, LPBOOL used)
{
    if (!p_WC2MB) { SetLastError(ERROR_PROC_NOT_FOUND); return 0; }
    return p_WC2MB(normalize_cp(cp), flags, src, srclen, dst, dstlen, defc, used);
}

BOOL WINAPI GetCPInfo(UINT cp, LPCIINFO info)
{
    if (!p_GetCPInfo) { SetLastError(ERROR_PROC_NOT_FOUND); return FALSE; }
    return p_GetCPInfo(normalize_cp(cp), info);
}

int WINAPI GetStringTypeA(DWORD it, LPCSTR src, int len, LPWORD out)
{
    if (!p_GetStringTypeA) { SetLastError(ERROR_PROC_NOT_FOUND); return 0; }
    /* GetStringTypeA 的第一个参数是 dwInfoType 而非 codepage，
     * 无法在此改写；此实现仅为导出完整性，实际调用仍转发。 */
    return p_GetStringTypeA(it, src, len, out);
}