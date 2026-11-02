import glob
import os
import sys
import tempfile

from runpython.core import run_log
from runpython.core.runner import Runner, RunState


def run_script(scripts_dir, name, code, values=None, python=sys.executable, timeout=60):
    p = scripts_dir / name
    p.write_text(code, encoding="utf-8")
    r = Runner()
    r.start(p, scripts_dir, python, values or {})
    res = r.wait_finish(timeout)
    assert res is not None, "execução não terminou"
    return res


def psr_temp_files():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "psr_*.json")))


def test_success_and_values(tmp_scripts_dir):
    before = psr_temp_files()
    res = run_script(tmp_scripts_dir, "ok.py",
                     "from psr import param\nX = param('int', default=1)\nprint('X =', X)\n",
                     {"X": 5})
    assert res.state == RunState.SUCCESS and res.exit_code == 0
    assert any(line.text == "X = 5" for line in res.lines)
    assert (tmp_scripts_dir / "psr.py").exists()  # helper copiado
    assert psr_temp_files() == before  # JSON temporário apagado
    assert run_log.last_result("ok.py")[0] == "SUCCESS"


def test_failure_exit_code(tmp_scripts_dir):
    before = psr_temp_files()
    res = run_script(tmp_scripts_dir, "f.py", "import sys\nprint('erro', file=sys.stderr)\nsys.exit(2)\n")
    assert res.state == RunState.FAILED and res.exit_code == 2
    assert any(line.stream == "err" and line.text == "erro" for line in res.lines)
    assert "erro" in res.stderr_tail
    assert psr_temp_files() == before


def test_unicode_output(tmp_scripts_dir):
    res = run_script(tmp_scripts_dir, "u.py", "print('ação ✓ 日本')\n")
    assert any(line.text == "ação ✓ 日本" for line in res.lines)


def test_many_lines(tmp_scripts_dir):
    res = run_script(tmp_scripts_dir, "m.py", "for i in range(10000):\n    print(i)\n")
    out = [line.text for line in res.lines if line.stream == "out"]
    assert len(out) == 10000 and out[-1] == "9999"
    log_text = res.log_path.read_text(encoding="utf-8")
    assert "\n9999\n" in log_text


def test_input_does_not_hang(tmp_scripts_dir):
    res = run_script(tmp_scripts_dir, "i.py", "input('> ')\n", timeout=20)
    assert res.state == RunState.FAILED
    assert any("EOFError" in t for t in res.stderr_tail)


def test_not_started_with_invalid_python(tmp_scripts_dir):
    before = psr_temp_files()
    res = run_script(tmp_scripts_dir, "x.py", "print(1)\n", python=r"C:\nao\existe\python.exe")
    assert res.state == RunState.NOT_STARTED and res.message
    assert psr_temp_files() == before


def test_abort(tmp_scripts_dir):
    p = tmp_scripts_dir / "lento.py"
    p.write_text("import time\nprint('inicio', flush=True)\ntime.sleep(60)\n", encoding="utf-8")
    r = Runner()
    r.start(p, tmp_scripts_dir, sys.executable, {})
    import time
    deadline = time.monotonic() + 20
    seen = False
    while time.monotonic() < deadline and not seen:
        for kind, payload in r.poll():
            if kind == "line" and payload.text == "inicio":
                seen = True
        time.sleep(0.05)
    assert seen
    r.abort()
    res = r.wait_finish(20)
    assert res.state == RunState.ABORTED
