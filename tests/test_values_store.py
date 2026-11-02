from runpython.core import paths
from runpython.core import values_store as vs
from runpython.psr import ParamSpec


def P(name, kind="text", **kw):
    return ParamSpec(name=name, kind=kind, **kw)


def test_save_and_load_roundtrip():
    vs.save("a.py", {"X": 1}, {"OLD": "z"})
    s = vs.load("a.py")
    assert s.values == {"X": 1} and s.orphans == {"OLD": "z"}


def test_new_param_uses_default():
    form, orphans, notes = vs.merge([P("X", default="d"), P("N", "int", required=True)],
                                    vs.StoredValues({"X": "salvo"}))
    assert form == {"X": "salvo", "N": None}
    assert orphans == {} and notes == []


def test_renamed_via_alias():
    form, orphans, _ = vs.merge([P("PASTA_ENTRADA", "folder", aliases=["PASTA"])],
                                vs.StoredValues({"PASTA": r"D:\x"}))
    assert form == {"PASTA_ENTRADA": r"D:\x"}
    assert orphans == {}


def test_removed_goes_to_orphans():
    form, orphans, notes = vs.merge([P("X")], vs.StoredValues({"X": "a", "Y": "b"}))
    assert orphans == {"Y": "b"}
    assert any("não é mais usado" in n for n in notes)


def test_orphan_restored_when_param_returns():
    form, orphans, _ = vs.merge([P("Y")], vs.StoredValues({}, {"Y": "volta"}))
    assert form == {"Y": "volta"} and orphans == {}


def test_type_changed_converts_or_falls_back():
    form, _, notes = vs.merge([P("X", "int", default=0)], vs.StoredValues({"X": "10"}))
    assert form == {"X": 10} and notes == []
    form, _, notes = vs.merge([P("X", "int", default=0)], vs.StoredValues({"X": "abc"}))
    assert form == {"X": 0} and notes


def test_option_removed_uses_default():
    form, _, notes = vs.merge([P("M", "choice", options=["a", "b"], default="a")],
                              vs.StoredValues({"M": "z"}))
    assert form == {"M": "a"}
    assert any("opção" in n for n in notes)


def test_corrupted_file_goes_to_bak():
    p = paths.values_dir() / "c.py.json"
    p.write_text("{nao é json", encoding="utf-8")
    s = vs.load("c.py")
    assert s.values == {}
    assert (paths.values_dir() / "c.py.json.bak").exists()
