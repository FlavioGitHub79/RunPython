import json
import sys

import pytest

from runpython import psr
from runpython.core import applog, config, paths, python_env, validation
from runpython.psr import ParamSpec


def test_config_roundtrip_and_defaults():
    assert config.load() == config.Config()
    cfg = config.Config(scripts_dir=r"D:\s", theme="dark", last_script="a.py")
    config.save(cfg)
    assert config.load() == cfg


def test_config_corrupted_or_unknown_keys():
    paths.config_path().write_text("{ruim", encoding="utf-8")
    assert config.load() == config.Config()
    paths.config_path().write_text(json.dumps({"theme": "neon", "extra": 1}), encoding="utf-8")
    assert config.load().theme == "system"


def test_python_env():
    assert python_env.resolve(config.Config()) == python_env.default_python()
    assert python_env.resolve(config.Config(python_path="x")) == "x"
    ok, version = python_env.check(sys.executable)
    assert ok and version[0] == "3"
    assert python_env.check(r"C:\nao\existe.exe") == (False, "Arquivo não encontrado")


def test_diagnostics_text(tmp_scripts_dir):
    applog.setup()
    applog.setup()  # idempotente
    text = applog.diagnostics_text(config.Config(scripts_dir=str(tmp_scripts_dir)), sys.executable)
    assert "RunPython" in text and "psr.py na pasta: (ausente)" in text


@pytest.mark.parametrize("kind,value,expected", [
    ("int", 3.0, (True, 3)), ("int", True, (False, None)), ("int", "x", (False, None)),
    ("float", 2, (True, 2.0)), ("float", "2,5", (True, 2.5)), ("float", [1], (False, None)),
    ("bool", 1, (False, None)), ("bool", True, (True, True)),
    ("text", 5, (True, "5")), ("text", [1], (False, None)), ("folder", None, (True, None)),
])
def test_coerce(kind, value, expected):
    assert validation.coerce(ParamSpec(name="X", kind=kind), value) == expected


def test_coerce_choice_by_string():
    s = ParamSpec(name="X", kind="choice", options=[1, 2])
    assert validation.coerce(s, "2") == (True, 2)


def test_bool_parse_strings():
    s = ParamSpec(name="X", kind="bool")
    assert validation.parse_value(s, "sim") == (True, None)
    assert validation.parse_value(s, "não") == (False, None)
    assert validation.parse_value(s, "talvez")[1]


# --- param() no mesmo processo --------------------------------------------------

@pytest.fixture
def fresh_psr(monkeypatch):
    monkeypatch.setattr(psr, "_values_state", psr._NOT_LOADED)
    monkeypatch.setattr(psr, "_scan_cache", {})
    return psr


def test_param_without_app_returns_default(fresh_psr, monkeypatch):
    monkeypatch.delenv("PSR_PARAMS_FILE", raising=False)
    assert fresh_psr.param("int", default=4) == 4


def test_param_reads_values_in_process(fresh_psr, monkeypatch, tmp_path):
    script = tmp_path / "s.py"
    script.write_text("from psr import param\nA = param('int', default=1)\n"
                      "B = param(\n  'text',\n  default='x')\n", encoding="utf-8")
    vals = tmp_path / "v.json"
    vals.write_text(json.dumps({"script_path": str(script), "values": {"A": 9, "B": "y"}}),
                    encoding="utf-8")
    monkeypatch.setenv("PSR_PARAMS_FILE", str(vals))
    ns = {"__name__": "s", "param": fresh_psr.param}
    code = compile(script.read_text(encoding="utf-8").replace("from psr import param\n", "\n"),
                   str(script), "exec")
    exec(code, ns)  # noqa: S102 - executa o script de teste para simular a chamada real
    assert ns["A"] == 9 and ns["B"] == "y"


def test_param_other_module_gets_default(fresh_psr, monkeypatch, tmp_path):
    vals = tmp_path / "v.json"
    vals.write_text(json.dumps({"script_path": str(tmp_path / "outro.py"), "values": {"A": 9}}),
                    encoding="utf-8")
    monkeypatch.setenv("PSR_PARAMS_FILE", str(vals))
    assert fresh_psr.param("int", default=1) == 1


def test_param_bad_values_file(fresh_psr, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PSR_PARAMS_FILE", str(tmp_path / "nao_existe.json"))
    assert fresh_psr.param("int", default=2) == 2
    assert "não foi possível ler" in capsys.readouterr().err


def test_param_unrecognized_line(fresh_psr, monkeypatch, tmp_path, capsys):
    vals = tmp_path / "v.json"
    vals.write_text(json.dumps({"values": {}}), encoding="utf-8")
    monkeypatch.setenv("PSR_PARAMS_FILE", str(vals))
    assert fresh_psr.param("int", default=3) == 3  # chamado daqui, sem marcador neste arquivo
    assert "não foi reconhecido" in capsys.readouterr().err
