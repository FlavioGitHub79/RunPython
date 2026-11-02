# RunPython

App Windows para executar scripts Python preenchendo os parâmetros numa janela, sem editar código.

Você carrega os scripts no app (botão **+**). O app encontra os parâmetros marcados com `param(...)`
(sem executar o script), monta o formulário, executa o script com log ao vivo e permite abortar.

## Requisitos

- Windows 10 ou 11
- Python 3.9 ou mais novo **com Tkinter** (no instalador do python.org, opção "tcl/tk and IDLE")
- Nada mais: o app usa só a biblioteca padrão (o visual é um tema próprio sobre o `clam` do Tkinter).

## Como usar

1. Dê dois cliques em `RunPython.pyw`. Na primeira vez, o app pergunta qual pasta de scripts usar
   (padrão: `Documentos\RunPython\scripts`).
2. Clique em **+** (ou "Carregar script") e escolha um `.py`. Ele é copiado para a pasta de scripts e
   aparece na lista. Só aparecem na lista os scripts carregados assim.
3. Preencha os campos e clique em **Iniciar execução** (ou Ctrl+Enter).

Atalhos e ações:

- **Ctrl+Z / Ctrl+Y** nos campos: desfazer / refazer.
- **F5** ou "Recarregar scripts": relê os scripts carregados (pega parâmetros novos).
- **Lixeira** no item da lista (ou botão direito → Remover da lista): tira o script da lista sem apagar o arquivo.

Para testar, carregue `examples/exemplo_relatorio.py`.

## Como preparar um script

Veja [docs/MARKER_SPEC.md](docs/MARKER_SPEC.md). Resumo:

```python
"""O que este script faz."""
from psr import param

PASTA = param("folder", default=r"C:\dados", label="Pasta de entrada", required=True)
LIMITE = param("int", default=100, label="Máximo de linhas")
```

## Onde ficam os dados

`%APPDATA%\RunPython`:

- `config.json`: pasta de scripts, lista de scripts carregados, Python escolhido, tema, tamanho da janela
- `values\<script>.json`: últimos valores usados em cada script
- `logs\<script>\*.log`: as 20 últimas execuções de cada script
- `app.log`: log do próprio app

## Desenvolvimento

```
python -m venv .venv
.venv\Scripts\python -m pip install pytest pytest-cov ruff
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check runpython tests
```

Design: [docs/designs/runpython.md](docs/designs/runpython.md).
