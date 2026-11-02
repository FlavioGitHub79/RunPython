"""param() dentro do script: valores do app, padrões na linha de comando, multiprocessing."""

import json
import os
import subprocess
import sys

SCRIPT = '''
from psr import param
import json, sys

A = param("int", default=1)
B = param(
    "text",
    default="padrão",
)
C = param("bool", default=False)

if __name__ == "__main__":
    print(json.dumps({"A": A, "B": B, "C": C}, ensure_ascii=False))
'''

MP_SCRIPT = '''
from psr import param
import multiprocessing as mp

V = param("int", default=1)

def child(q):
    q.put(V)

if __name__ == "__main__":
    q = mp.Queue()
    p = mp.Process(target=child, args=(q,))
    p.start()
    print("child", q.get(timeout=30))
    p.join()
'''


def run(script, env_extra=None):
    env = dict(os.environ)
    env.pop("PSR_PARAMS_FILE", None)
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_extra or {})
    out = subprocess.run([sys.executable, str(script)], cwd=str(script.parent), env=env,
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr
    return out.stdout


def write_values(tmp_path, script, values):
    p = tmp_path / "vals.json"
    p.write_text(json.dumps({"format": 1, "script": script.name, "script_path": str(script),
                             "values": values}), encoding="utf-8")
    return {"PSR_PARAMS_FILE": str(p)}


def test_defaults_without_app(scripts_with_psr):
    s = scripts_with_psr / "s.py"
    s.write_text(SCRIPT, encoding="utf-8")
    assert json.loads(run(s)) == {"A": 1, "B": "padrão", "C": False}


def test_values_from_app_including_multiline(scripts_with_psr, tmp_path):
    s = scripts_with_psr / "s.py"
    s.write_text(SCRIPT, encoding="utf-8")
    env = write_values(tmp_path, s, {"A": 42, "B": "olá", "C": True})
    assert json.loads(run(s, env)) == {"A": 42, "B": "olá", "C": True}


def test_missing_key_uses_default(scripts_with_psr, tmp_path):
    s = scripts_with_psr / "s.py"
    s.write_text(SCRIPT, encoding="utf-8")
    env = write_values(tmp_path, s, {"A": 7})
    assert json.loads(run(s, env)) == {"A": 7, "B": "padrão", "C": False}


def test_multiprocessing_child_gets_values(scripts_with_psr, tmp_path):
    s = scripts_with_psr / "mp.py"
    s.write_text(MP_SCRIPT, encoding="utf-8")
    env = write_values(tmp_path, s, {"V": 99})
    assert "child 99" in run(s, env)
