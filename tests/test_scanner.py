import os
import time

import pytest

from runpython.core.scanner import ScriptLibrary, find_legacy_scripts, params_signature


def test_only_registered_scripts_are_listed(tmp_scripts_dir):
    a = tmp_scripts_dir / "a.py"
    a.write_text("print(1)")
    (tmp_scripts_dir / "nao_carregado.py").write_text("print(2)")
    lib = ScriptLibrary(tmp_scripts_dir, [str(a)])
    assert [e.name for e in lib.refresh()] == ["a.py"]
    assert lib.get("nao_carregado.py") is None


def test_missing_registered_file(tmp_scripts_dir):
    lib = ScriptLibrary(tmp_scripts_dir, [str(tmp_scripts_dir / "sumiu.py")])
    e = lib.refresh()[0]
    assert e.missing and e.scan is None


def test_remove_keeps_file(tmp_scripts_dir):
    a = tmp_scripts_dir / "a.py"
    a.write_text("print(1)")
    lib = ScriptLibrary(tmp_scripts_dir, [str(a)])
    lib.refresh()
    lib.remove("a.py")
    assert lib.refresh() == [] and lib.registered() == []
    assert a.exists()


def test_legacy_listing(tmp_scripts_dir):
    for n in ("b.py", "A.py", "psr.py", "_priv.py", "nota.txt"):
        (tmp_scripts_dir / n).write_text("")
    (tmp_scripts_dir / "sub").mkdir()
    assert [p.name for p in find_legacy_scripts(tmp_scripts_dir)] == ["A.py", "b.py"]


def test_reuses_scan_when_mtime_unchanged(tmp_scripts_dir):
    a = tmp_scripts_dir / "a.py"
    a.write_text("print(1)")
    lib = ScriptLibrary(tmp_scripts_dir, [str(a)])
    first = lib.refresh()[0].scan
    assert lib.refresh()[0].scan is first


def test_get_rescans_when_changed(tmp_scripts_dir):
    p = tmp_scripts_dir / "a.py"
    p.write_text("from psr import param\nX = param('int')\n")
    lib = ScriptLibrary(tmp_scripts_dir, [str(p)])
    lib.refresh()
    p.write_text("from psr import param\nX = param('int')\nY = param('text')\n")
    t = time.time() + 5
    os.utime(p, (t, t))
    e = lib.get("a.py")
    assert [s.name for s in e.scan.params] == ["X", "Y"]


def test_signature_changes_with_params():
    from runpython.psr import scan_source
    a = scan_source("from psr import param\nX = param('int')\n")
    b = scan_source("from psr import param\nX = param('int', required=True)\n")
    assert params_signature(a) != params_signature(b)
    assert params_signature(a) == params_signature(scan_source("from psr import param\nX = param('int')\n"))


def test_add_script_copies_and_registers(tmp_scripts_dir, tmp_path):
    src = tmp_path / "novo.py"
    src.write_text("print('v1')")
    lib = ScriptLibrary(tmp_scripts_dir)
    e = lib.add_script(src)
    assert e.name == "novo.py" and (tmp_scripts_dir / "novo.py").exists()
    assert lib.registered() == [str(tmp_scripts_dir / "novo.py")]
    src.write_text("print('v2')")
    with pytest.raises(FileExistsError):
        lib.add_script(src)
    lib.add_script(src, overwrite=True)
    assert "v2" in (tmp_scripts_dir / "novo.py").read_text()


def test_add_script_already_in_folder(tmp_scripts_dir):
    a = tmp_scripts_dir / "a.py"
    a.write_text("print(1)")
    lib = ScriptLibrary(tmp_scripts_dir)
    assert lib.add_script(a).name == "a.py"  # mesmo arquivo: só registra, sem perguntar
    assert lib.is_registered("a.py")


def test_add_script_conflicts_with_unregistered_file(tmp_scripts_dir, tmp_path):
    (tmp_scripts_dir / "x.py").write_text("print('da pasta')")
    src = tmp_path / "x.py"
    src.write_text("print('de fora')")
    lib = ScriptLibrary(tmp_scripts_dir)
    with pytest.raises(FileExistsError):
        lib.add_script(src)
