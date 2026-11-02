import textwrap

import pytest

from runpython.psr import scan_file, scan_source


def scan(src: str):
    return scan_source(textwrap.dedent(src), "t.py")


FULL = '''
"""Gera o relatório mensal."""
# psr-format: 1
from psr import param

PASTA = param("folder", default=r"C:\\dados", label="Pasta", group="Arquivos", required=True)
SAIDA = param("file", default="saida.csv", filetypes=[("CSV", "*.csv")], save=True, group="Arquivos")
LIMITE = param("int", default=10, min=1, max=100, group="Execução")
FATOR = param("float", default=1.5)
MODO = param("choice", default="csv", options=["csv", "xlsx"])
SIMULAR = param("bool", default=False, help="Não grava nada.")
NOME = param("text", default="x", aliases=["NOME_ANTIGO"])
'''


def test_all_kinds():
    r = scan(FULL)
    assert r.ok, r.issues
    assert r.description == "Gera o relatório mensal."
    assert r.format == 1
    assert [p.name for p in r.params] == ["PASTA", "SAIDA", "LIMITE", "FATOR", "MODO", "SIMULAR", "NOME"]
    by = {p.name: p for p in r.params}
    assert by["PASTA"].kind == "folder" and by["PASTA"].required and by["PASTA"].group == "Arquivos"
    assert by["PASTA"].default == "C:\\dados"
    assert by["SAIDA"].save and not by["SAIDA"].must_exist
    assert by["SAIDA"].filetypes == [("CSV", "*.csv")]
    assert by["LIMITE"].min == 1 and by["LIMITE"].max == 100
    assert by["MODO"].options == ["csv", "xlsx"]
    assert by["SIMULAR"].help == "Não grava nada."
    assert by["NOME"].aliases == ["NOME_ANTIGO"]
    assert by["FATOR"].display_label == "FATOR"
    assert not r.warnings


def test_multiline_call_has_line_range():
    r = scan('''
        from psr import param
        X = param(
            "int",
            default=3,
        )
    ''')
    assert r.ok
    assert r.params[0].lineno == 3 and r.params[0].end_lineno == 6


def test_attribute_form():
    r = scan('import psr\nX = psr.param("text", default="a")\n')
    assert r.ok and r.params[0].name == "X"


@pytest.mark.parametrize("src,fragment", [
    ('from psr import param\nX = param("int", default=CONST)\n', "precisa ser literal"),
    ('from psr import param\nif True:\n    X = param("int")\n', "nível do módulo"),
    ('from psr import param\ndef f():\n    X = param("int")\n', "nível do módulo"),
    ('from psr import param\nX = param("date")\n', "tipo desconhecido"),
    ('from psr import param\nX = param("int")\nX = param("int")\n', "nome repetido"),
    ('from psr import param\nX = param("choice")\n', "exige options"),
    ('from psr import param\nX = param("choice", options=["a"], default="b")\n', "default precisa estar"),
    ('from psr import param\nX = param("int", default="a")\n', "inteiro"),
    ('from psr import param\nX = param("int", min=5, max=1)\n', "min é maior"),
    ('from psr import param\nX = param()\n', "falta o tipo"),
    ('from psr import param\nX, Y = param("int"), 1\n', None),  # não é param() direto: ignorado como marcador?
    ('from psr import param\nX = param("int", "extra")\n', "posicional"),
    ('X = (\n', "erro de sintaxe"),
    ('# psr-format: 2\nfrom psr import param\n', "versão mais nova"),
])
def test_marker_errors(src, fragment):
    r = scan_source(src, "t.py")
    if fragment is None:
        # tupla: a chamada param() fica fora de uma atribuição simples -> erro de nível do módulo
        assert not r.ok
        return
    assert not r.ok
    assert any(fragment in i.message for i in r.errors), r.issues


def test_unknown_key_is_warning():
    r = scan('from psr import param\nX = param("int", cor="azul")\n')
    assert r.ok
    assert r.params[0].name == "X"
    assert any("desconhecido" in w.message for w in r.warnings)


def test_missing_import_is_warning():
    r = scan('X = param("int")\n')
    assert r.ok
    assert any("from psr import param" in w.message for w in r.warnings)


def test_no_params_and_no_format():
    r = scan('"""Só imprime."""\nprint("oi")\n')
    assert r.ok and r.params == [] and r.format == 1 and r.description == "Só imprime."


def test_bad_param_does_not_hide_good_ones():
    r = scan('from psr import param\nA = param("int", default=1)\nB = param("xyz")\n')
    assert not r.ok
    assert [p.name for p in r.params] == ["A"]


def test_cp1252_with_coding_declaration(tmp_path):
    p = tmp_path / "s.py"
    p.write_bytes('# -*- coding: cp1252 -*-\nfrom psr import param\nX = param("text", label="Ação")\n'
                  .encode("cp1252"))
    r = scan_file(str(p))
    assert r.ok and r.params[0].label == "Ação"


def test_utf8_bom(tmp_path):
    p = tmp_path / "s.py"
    p.write_bytes(b"\xef\xbb\xbf" + 'from psr import param\nX = param("text", label="Olá")\n'.encode())
    r = scan_file(str(p))
    assert r.ok and r.params[0].label == "Olá"


def test_unreadable_file(tmp_path):
    r = scan_file(str(tmp_path / "nao_existe.py"))
    assert not r.ok and "não foi possível ler" in r.errors[0].message
