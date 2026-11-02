from runpython.core.error_hints import find_hint

PY = r"C:\Python\python.exe"


def test_known_mapping():
    h = find_hint(["Traceback...", "ModuleNotFoundError: No module named 'cv2'"], PY)
    assert h.title == "Falta o pacote opencv-python"
    assert h.command == f'"{PY}" -m pip install opencv-python'


def test_unknown_module_uses_own_name():
    h = find_hint(["ModuleNotFoundError: No module named 'pandas.core'"], PY)
    assert h.title == "Falta o pacote pandas"


def test_psr_missing():
    h = find_hint(["ModuleNotFoundError: No module named 'psr'"], PY)
    assert "psr.py" in h.title and not h.command


def test_file_not_found():
    h = find_hint(["FileNotFoundError: [Errno 2] No such file or directory: 'C:/x.csv'"], PY)
    assert h.title.startswith("Arquivo") and "C:/x.csv" in h.detail


def test_no_hint():
    assert find_hint(["ValueError: algo"], PY) is None
    assert find_hint([], PY) is None
