import os
import stat

import pytest

from runpython.core import helper_install as hi
from runpython.core import paths


def test_installs_when_missing(tmp_scripts_dir):
    r = hi.ensure_helper(tmp_scripts_dir)
    assert r.action == "installed"
    assert hi.read_version(tmp_scripts_dir / "psr.py") == hi.read_version(paths.bundled_psr_path())


def test_noop_when_same_version(tmp_scripts_dir):
    hi.ensure_helper(tmp_scripts_dir)
    assert hi.ensure_helper(tmp_scripts_dir).action == "ok"


def test_updates_when_version_differs(tmp_scripts_dir):
    (tmp_scripts_dir / "psr.py").write_text('PSR_VERSION = "0.0.1"\n', encoding="utf-8")
    r = hi.ensure_helper(tmp_scripts_dir)
    assert r.action == "updated"
    assert "def param(" in (tmp_scripts_dir / "psr.py").read_text(encoding="utf-8")


def test_error_on_unwritable_target(tmp_scripts_dir, monkeypatch):
    def boom(*a, **k):
        raise PermissionError("negado")
    monkeypatch.setattr(paths, "atomic_write_text", boom)
    with pytest.raises(hi.HelperInstallError):
        hi.ensure_helper(tmp_scripts_dir)


def test_read_version_missing(tmp_path):
    assert hi.read_version(tmp_path / "x.py") is None


def test_readonly_existing_old_file(tmp_scripts_dir):
    target = tmp_scripts_dir / "psr.py"
    target.write_text('PSR_VERSION = "0.0.1"\n', encoding="utf-8")
    os.chmod(target, stat.S_IREAD)
    try:
        with pytest.raises(hi.HelperInstallError):
            hi.ensure_helper(tmp_scripts_dir)
    finally:
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
