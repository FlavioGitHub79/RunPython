from runpython.core import validation as v
from runpython.psr import ParamSpec


def spec(kind, **kw):
    return ParamSpec(name="X", kind=kind, **kw)


def test_int():
    s = spec("int", min=1, max=10)
    assert v.check(s, "5") == (5, None)
    assert v.check(s, "-3")[1] == "O mínimo é 1"
    assert v.check(s, "11")[1] == "O máximo é 10"
    assert v.check(s, "1,5")[1] == "Informe um número inteiro"
    assert v.check(s, "") == (None, None)


def test_float_accepts_comma():
    s = spec("float")
    assert v.check(s, "3,5") == (3.5, None)
    assert v.check(s, "3.5") == (3.5, None)
    assert v.check(s, "abc")[1].startswith("Informe um número")


def test_required():
    assert v.check(spec("text", required=True), "  ")[1] == "Campo obrigatório"
    assert v.check(spec("int", required=True), "")[1] == "Campo obrigatório"
    assert v.check(spec("text"), "") == ("", None)


def test_choice_keeps_option_type():
    s = spec("choice", options=[1, 2, 3])
    assert v.check(s, "2") == (2, None)
    assert v.check(s, "9")[1] == "Escolha uma das opções"


def test_bool():
    assert v.check(spec("bool"), True) == (True, None)
    assert v.check(spec("bool"), False) == (False, None)


def test_file_and_folder(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    assert v.check(spec("file"), str(f)) == (str(f), None)
    assert v.check(spec("file"), str(tmp_path / "nao.txt"))[1] == "O arquivo não existe"
    assert v.check(spec("file", must_exist=False), str(tmp_path / "nao.txt"))[1] is None
    save = spec("file", save=True, must_exist=False)
    assert v.check(save, str(tmp_path / "novo.csv"))[1] is None
    assert v.check(save, str(tmp_path / "x" / "y" / "novo.csv"))[1] == "A pasta de destino não existe"
    assert v.check(spec("folder"), str(tmp_path))[1] is None
    assert v.check(spec("folder"), str(tmp_path / "nao"))[1] == "A pasta não existe"
    assert v.check(spec("folder"), "") == (None, None)


def test_to_raw_roundtrip():
    s = spec("float")
    assert v.to_raw(s, 3.5) == "3,5"
    assert v.check(s, v.to_raw(s, 3.5))[0] == 3.5
    assert v.to_raw(spec("int"), None) == ""
    assert v.to_raw(spec("bool"), None) is False


def test_validate_all():
    specs = [spec("int"), ParamSpec(name="Y", kind="text", required=True)]
    values, errors = v.validate_all(specs, {"X": "4", "Y": ""})
    assert values == {"X": 4}
    assert errors == {"Y": "Campo obrigatório"}
