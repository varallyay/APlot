/*
 * APlot.exe - the launcher of APlot on Windows.
 *
 * APlot is one Python file, aplot.py, installed beside this program.  The
 * launcher looks for a Python 3 that has what APlot needs (tkinter, numpy,
 * pandas and matplotlib) and starts aplot.py with it, handing on the
 * arguments (a graph opened from the Explorer, say).  It looks, in order:
 *
 *   1. at the Python named by the environment variable APLOT_PYTHON,
 *   2. at a Python beside this program (python\pythonw.exe),
 *   3. at conda: Anaconda, Miniconda and Miniforge in the usual places
 *      (the recommended Python),
 *   4. at every Python registered by its installer (python.org, the
 *      Microsoft Store), the newest first.
 *
 * When none of them has the packages, the first Python found is used all
 * the same - APlot then says itself what is missing and how to install it;
 * when there is no Python at all, a message says where to get one.
 *
 * Built with mingw-w64 on Linux (see packaging/build_packages.py):
 *   x86_64-w64-mingw32-gcc -municode -mwindows -O2 -static -s \
 *       -o APlot.exe launcher.c launcher.res -lshell32 -ladvapi32
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdlib.h>

#define MAX_CANDIDATES 64
#define LONG_PATH 4096

static wchar_t *candidates[MAX_CANDIDATES];
static int candidate_count = 0;

static const wchar_t *NEEDS =
    L"import importlib.util as u, sys; "
    L"sys.exit(0 if all(u.find_spec(m) for m in "
    L"('tkinter', 'numpy', 'pandas', 'matplotlib')) else 1)";

static int file_exists(const wchar_t *path)
{
    DWORD attributes = GetFileAttributesW(path);
    return attributes != INVALID_FILE_ATTRIBUTES
        && !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

static void add_candidate(const wchar_t *path)
{
    int i;
    if (path == NULL || !path[0] || candidate_count >= MAX_CANDIDATES)
        return;
    if (!file_exists(path))
        return;
    for (i = 0; i < candidate_count; i++)
        if (_wcsicmp(candidates[i], path) == 0)
            return;
    candidates[candidate_count++] = _wcsdup(path);
}

/* <folder>\pythonw.exe, for a folder given by an environment variable */
static void add_in(const wchar_t *variable, const wchar_t *tail)
{
    wchar_t base[LONG_PATH], path[LONG_PATH];
    DWORD got = GetEnvironmentVariableW(variable, base, LONG_PATH);
    if (got == 0 || got >= LONG_PATH)
        return;
    _snwprintf(path, LONG_PATH, L"%s\\%s\\pythonw.exe", base, tail);
    path[LONG_PATH - 1] = 0;
    add_candidate(path);
}

/* a key of HKCU or HKLM\Software\Python\PythonCore\<tag>\InstallPath */
static void add_registered(HKEY root, REGSAM view)
{
    HKEY core;
    DWORD index;
    wchar_t tags[32][128];
    int tag_count = 0, i, j;
    if (RegOpenKeyExW(root, L"Software\\Python\\PythonCore", 0,
                      KEY_READ | view, &core) != ERROR_SUCCESS)
        return;
    for (index = 0; tag_count < 32; index++) {
        DWORD size = 128;
        if (RegEnumKeyExW(core, index, tags[tag_count], &size,
                          NULL, NULL, NULL, NULL) != ERROR_SUCCESS)
            break;
        tag_count++;
    }
    /* the newest first: "3.13" before "3.12" before "3.9" */
    for (i = 0; i < tag_count; i++)
        for (j = i + 1; j < tag_count; j++) {
            int a_major = 0, a_minor = 0, b_major = 0, b_minor = 0;
            swscanf(tags[i], L"%d.%d", &a_major, &a_minor);
            swscanf(tags[j], L"%d.%d", &b_major, &b_minor);
            if (b_major > a_major || (b_major == a_major && b_minor > a_minor)) {
                wchar_t swap[128];
                wcscpy(swap, tags[i]);
                wcscpy(tags[i], tags[j]);
                wcscpy(tags[j], swap);
            }
        }
    for (i = 0; i < tag_count; i++) {
        wchar_t sub[256], value[LONG_PATH], path[LONG_PATH];
        DWORD size, type;
        HKEY install;
        if (tags[i][0] != L'3')
            continue;
        _snwprintf(sub, 256, L"%s\\InstallPath", tags[i]);
        sub[255] = 0;
        if (RegOpenKeyExW(core, sub, 0, KEY_READ | view, &install) != ERROR_SUCCESS)
            continue;
        size = sizeof(value);
        if (RegQueryValueExW(install, L"WindowedExecutablePath", NULL, &type,
                             (BYTE *)value, &size) == ERROR_SUCCESS && type == REG_SZ) {
            add_candidate(value);
        }
        size = sizeof(value);
        if (RegQueryValueExW(install, NULL, NULL, &type, (BYTE *)value,
                             &size) == ERROR_SUCCESS && type == REG_SZ) {
            size_t length = wcslen(value);
            if (length && value[length - 1] == L'\\')
                value[length - 1] = 0;
            _snwprintf(path, LONG_PATH, L"%s\\pythonw.exe", value);
            path[LONG_PATH - 1] = 0;
            add_candidate(path);
        }
        RegCloseKey(install);
    }
    RegCloseKey(core);
}

/* the folder of a file, without the last backslash */
static void folder_of(const wchar_t *path, wchar_t *folder)
{
    wchar_t *slash;
    wcsncpy(folder, path, LONG_PATH - 1);
    folder[LONG_PATH - 1] = 0;
    slash = wcsrchr(folder, L'\\');
    if (slash)
        *slash = 0;
}

/* conda keeps the DLLs of its packages in Library\bin: they are found when
   that folder is on the PATH, as an activated conda environment has it */
static void prepare_environment(const wchar_t *python)
{
    static wchar_t original[32767];
    static int saved = 0;
    wchar_t home[LONG_PATH], library[LONG_PATH], path[32767];
    if (!saved) {
        if (!GetEnvironmentVariableW(L"PATH", original, 32767))
            original[0] = 0;
        saved = 1;
    }
    folder_of(python, home);
    _snwprintf(library, LONG_PATH, L"%s\\Library\\bin", home);
    library[LONG_PATH - 1] = 0;
    if (GetFileAttributesW(library) != INVALID_FILE_ATTRIBUTES) {
        _snwprintf(path, 32767,
                   L"%s;%s\\Library\\mingw-w64\\bin;%s\\Library\\usr\\bin;"
                   L"%s\\Library\\bin;%s\\Scripts;%s\\bin;%s",
                   home, home, home, home, home, home, original);
        path[32766] = 0;
        SetEnvironmentVariableW(L"PATH", path);
    } else {
        SetEnvironmentVariableW(L"PATH", original);
    }
}

/* run a command line hidden; its exit code, or -1 */
static long run_hidden(wchar_t *command, DWORD wait_ms)
{
    STARTUPINFOW start;
    PROCESS_INFORMATION process;
    DWORD code = (DWORD)-1;
    ZeroMemory(&start, sizeof(start));
    start.cb = sizeof(start);
    ZeroMemory(&process, sizeof(process));
    if (!CreateProcessW(NULL, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, NULL, &start, &process))
        return -1;
    if (WaitForSingleObject(process.hProcess, wait_ms) != WAIT_OBJECT_0) {
        TerminateProcess(process.hProcess, 1);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
        return -1;
    }
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return (long)code;
}

static int has_packages(const wchar_t *python)
{
    static wchar_t command[LONG_PATH * 2];
    prepare_environment(python);
    _snwprintf(command, LONG_PATH * 2, L"\"%s\" -c \"%s\"", python, NEEDS);
    command[LONG_PATH * 2 - 1] = 0;
    return run_hidden(command, 60000) == 0;
}

/* what comes after the name of this program on its command line */
static const wchar_t *arguments(void)
{
    const wchar_t *line = GetCommandLineW();
    if (*line == L'"') {
        line++;
        while (*line && *line != L'"')
            line++;
        if (*line == L'"')
            line++;
    } else {
        while (*line && *line != L' ' && *line != L'\t')
            line++;
    }
    while (*line == L' ' || *line == L'\t')
        line++;
    return line;
}

static int start_aplot(const wchar_t *python, const wchar_t *program,
                       const wchar_t *folder)
{
    STARTUPINFOW start;
    PROCESS_INFORMATION process;
    size_t size = wcslen(python) + wcslen(program) + wcslen(arguments()) + 16;
    wchar_t *command = (wchar_t *)malloc(size * sizeof(wchar_t));
    if (command == NULL)
        return 0;
    prepare_environment(python);
    _snwprintf(command, size, L"\"%s\" \"%s\" %s", python, program, arguments());
    command[size - 1] = 0;
    ZeroMemory(&start, sizeof(start));
    start.cb = sizeof(start);
    ZeroMemory(&process, sizeof(process));
    if (!CreateProcessW(NULL, command, NULL, NULL, FALSE, 0, NULL, folder,
                        &start, &process)) {
        free(command);
        return 0;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    free(command);
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR line, int show)
{
    wchar_t self[LONG_PATH], folder[LONG_PATH], program[LONG_PATH], path[LONG_PATH];
    DWORD got;
    int i;
    (void)instance; (void)previous; (void)line; (void)show;

    got = GetModuleFileNameW(NULL, self, LONG_PATH);
    if (got == 0 || got >= LONG_PATH)
        return 1;
    folder_of(self, folder);
    _snwprintf(program, LONG_PATH, L"%s\\aplot.py", folder);
    program[LONG_PATH - 1] = 0;
    if (!file_exists(program)) {
        MessageBoxW(NULL, L"aplot.py is missing beside APlot.exe.\n\n"
                    L"Install APlot again.", L"APlot", MB_OK | MB_ICONERROR);
        return 1;
    }

    got = GetEnvironmentVariableW(L"APLOT_PYTHON", path, LONG_PATH);
    if (got > 0 && got < LONG_PATH)
        add_candidate(path);
    _snwprintf(path, LONG_PATH, L"%s\\python\\pythonw.exe", folder);
    path[LONG_PATH - 1] = 0;
    add_candidate(path);
    add_in(L"USERPROFILE", L"anaconda3");
    add_in(L"USERPROFILE", L"miniconda3");
    add_in(L"USERPROFILE", L"miniforge3");
    add_in(L"LOCALAPPDATA", L"anaconda3");
    add_in(L"LOCALAPPDATA", L"miniconda3");
    add_in(L"LOCALAPPDATA", L"miniforge3");
    add_in(L"ProgramData", L"anaconda3");
    add_in(L"ProgramData", L"miniconda3");
    add_in(L"ProgramData", L"miniforge3");
    add_in(L"SystemDrive", L"anaconda3");
    add_registered(HKEY_CURRENT_USER, 0);
    add_registered(HKEY_LOCAL_MACHINE, KEY_WOW64_64KEY);
    add_registered(HKEY_LOCAL_MACHINE, KEY_WOW64_32KEY);

    for (i = 0; i < candidate_count; i++)
        if (has_packages(candidates[i]))
            return start_aplot(candidates[i], program, folder) ? 0 : 1;
    if (candidate_count > 0)      /* APlot says itself what is missing */
        return start_aplot(candidates[0], program, folder) ? 0 : 1;

    if (MessageBoxW(NULL,
            L"APlot needs Python 3 with the packages numpy, pandas and "
            L"matplotlib, and this computer has no Python yet.\n\n"
            L"The recommended Python is Anaconda, which brings all of them. "
            L"Install it, then start APlot again.\n\n"
            L"Open the download page of Anaconda now?",
            L"APlot", MB_YESNO | MB_ICONINFORMATION) == IDYES)
        ShellExecuteW(NULL, L"open", L"https://www.anaconda.com/download",
                      NULL, NULL, SW_SHOWNORMAL);
    return 1;
}
