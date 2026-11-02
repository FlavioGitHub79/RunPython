import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BUNDLED_PSR = ROOT / "runpython" / "psr.py"


@pytest.fixture(autouse=True)
def appdata_tmp(tmp_path, monkeypatch):
    """Redireciona %APPDATA% para uma pasta temporária em todos os testes."""
    d = tmp_path / "appdata"
    d.mkdir()
    monkeypatch.setenv("APPDATA", str(d))
    return d


@pytest.fixture
def tmp_scripts_dir(tmp_path):
    d = tmp_path / "scripts"
    d.mkdir()
    return d


@pytest.fixture
def scripts_with_psr(tmp_scripts_dir):
    shutil.copy(BUNDLED_PSR, tmp_scripts_dir / "psr.py")
    return tmp_scripts_dir


def write(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_text(text, encoding=encoding)
    return path
