"""Garante que ler os marcadores NUNCA executa o script (objetivo G2)."""

from runpython.core.scanner import ScriptLibrary
from runpython.psr import scan_file

MALICIOUS = '''
import sys, socket, pathlib
pathlib.Path(r"{marker}").write_text("executou")
socket.create_connection(("127.0.0.1", 9), timeout=0.1)
sys.exit(3)
from psr import param
X = param("int", default=1)
'''


def test_scan_does_not_execute(tmp_path):
    marker = tmp_path / "executou.txt"
    script = tmp_path / "mal.py"
    script.write_text(MALICIOUS.format(marker=marker), encoding="utf-8")

    r = scan_file(str(script))
    assert r.ok and r.params[0].name == "X"

    lib = ScriptLibrary(tmp_path, [str(script)])
    lib.refresh()
    lib.get("mal.py")
    lib.rescan("mal.py")

    assert not marker.exists()
