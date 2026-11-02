"""Job Object do Windows: encerra o script e todos os processos filhos de uma vez."""

from __future__ import annotations

import logging
import subprocess
import sys

log = logging.getLogger(__name__)

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectExtendedLimitInformation = 9
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateJobObject.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL


class Job:
    """Agrupa um processo e seus filhos. Se algo falhar, usa taskkill /T como alternativa."""

    def __init__(self) -> None:
        self._handle = None
        self._pid = None
        if sys.platform != "win32":
            return
        try:
            h = _k32.CreateJobObjectW(None, None)
            if not h:
                raise ctypes.WinError(ctypes.get_last_error())
            if not self._set_flags(h, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE):
                _k32.CloseHandle(h)
                raise ctypes.WinError(ctypes.get_last_error())
            self._handle = h
        except OSError as e:
            log.warning("Job Object indisponível, usando taskkill: %s", e)
            self._handle = None

    @staticmethod
    def _set_flags(handle, flags: int) -> bool:
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = flags
        return bool(_k32.SetInformationJobObject(
            handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)))

    @property
    def active(self) -> bool:
        return self._handle is not None

    def assign(self, pid: int) -> None:
        self._pid = pid
        if self._handle is None:
            return
        hproc = _k32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not hproc:
            log.warning("OpenProcess falhou para PID %s", pid)
            self.close()
            return
        try:
            if not _k32.AssignProcessToJobObject(self._handle, hproc):
                log.warning("AssignProcessToJobObject falhou: %s", ctypes.get_last_error())
                self.close()
        finally:
            _k32.CloseHandle(hproc)

    def terminate(self, exit_code: int = 1) -> None:
        if self._handle is not None:
            if _k32.TerminateJobObject(self._handle, exit_code):
                return
            log.warning("TerminateJobObject falhou: %s", ctypes.get_last_error())
        if self._pid is not None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self._pid)],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)

    def release(self) -> None:
        """Fim normal: libera o job SEM matar processos que o script deixou abertos
        (ex.: um Excel aberto pelo script)."""
        if self._handle is not None:
            self._set_flags(self._handle, 0)
        self.close()

    def close(self) -> None:
        if self._handle is not None:
            _k32.CloseHandle(self._handle)
            self._handle = None
