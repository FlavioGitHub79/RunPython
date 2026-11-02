"""Abortar encerra o script E os processos filhos (CUJ 4)."""

import sys
import time

import pytest

from runpython.core.runner import Runner, RunState

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="só Windows")

SCRIPT = '''
import multiprocessing as mp, os, time

def dorme():
    time.sleep(60)

if __name__ == "__main__":
    filhos = [mp.Process(target=dorme) for _ in range(2)]
    for f in filhos:
        f.start()
    print("PIDS", os.getpid(), *[f.pid for f in filhos], flush=True)
    time.sleep(60)
'''


def alive(pid: int) -> bool:
    import ctypes
    k32 = ctypes.WinDLL("kernel32")
    SYNCHRONIZE, QUERY = 0x00100000, 0x1000
    h = k32.OpenProcess(SYNCHRONIZE | QUERY, False, pid)
    if not h:
        return False
    try:
        return k32.WaitForSingleObject(h, 0) == 0x102  # WAIT_TIMEOUT => ainda vivo
    finally:
        k32.CloseHandle(h)


def test_abort_kills_children(tmp_scripts_dir):
    p = tmp_scripts_dir / "mp.py"
    p.write_text(SCRIPT, encoding="utf-8")
    r = Runner()
    r.start(p, tmp_scripts_dir, sys.executable, {})
    pids = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and pids is None:
        for kind, payload in r.poll():
            if kind == "line" and payload.text.startswith("PIDS"):
                pids = [int(x) for x in payload.text.split()[1:]]
        time.sleep(0.05)
    assert pids and len(pids) == 3
    assert all(alive(pid) for pid in pids)

    r.abort()
    res = r.wait_finish(20)
    assert res.state == RunState.ABORTED

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and any(alive(pid) for pid in pids):
        time.sleep(0.1)
    assert not any(alive(pid) for pid in pids)


def test_normal_exit_does_not_kill_detached_leftovers(tmp_scripts_dir):
    """No fim normal o job é liberado sem matar o que o script deixou aberto."""
    p = tmp_scripts_dir / "deixa.py"
    p.write_text(
        "import subprocess, sys\n"
        "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print('FILHO', c.pid, flush=True)\n",
        encoding="utf-8")
    r = Runner()
    r.start(p, tmp_scripts_dir, sys.executable, {})
    res = r.wait_finish(30)
    assert res.state == RunState.SUCCESS
    pid = int(next(line.text.split()[1] for line in res.lines if line.text.startswith("FILHO")))
    time.sleep(0.5)
    try:
        assert alive(pid)
    finally:
        import subprocess
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
