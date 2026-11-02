# Especificação dos marcadores do RunPython (`psr-format: 1`)

Este documento é para quem **escreve ou converte** scripts para rodar no RunPython.

## Como funciona

1. Você marca no script quais variáveis são parâmetros, usando `param(...)`.
2. O RunPython **lê o texto do script sem executá-lo** e monta um campo na tela para cada `param(...)`.
3. Na execução, o RunPython entrega os valores preenchidos ao script. Dentro do script, cada `param(...)` devolve o valor da tela.
4. Pela linha de comando (`python meu_script.py`), cada `param(...)` devolve o seu `default`.

O módulo `psr.py` fica na pasta dos scripts. O RunPython o copia e atualiza sozinho antes de cada execução; **não edite essa cópia**.

## Exemplo mínimo

```python
"""Gera o relatório mensal a partir das planilhas de entrada."""
# psr-format: 1
from psr import param

PASTA = param("folder", default=r"C:\dados", label="Pasta de entrada", required=True)
LIMITE = param("int", default=1000, label="Máximo de linhas", min=1)

print(PASTA, LIMITE)
```

- A **docstring** do início do arquivo vira a descrição na tela.
- `# psr-format: 1` é opcional (sem ele, vale 1).
- O arquivo completo de referência é [examples/exemplo_relatorio.py](../examples/exemplo_relatorio.py).

## Tipos

| Tipo | Campo na tela | Valor que o script recebe |
| :-- | :-- | :-- |
| `"text"` | caixa de texto | `str` |
| `"int"` | número inteiro | `int`, ou `None` se vazio |
| `"float"` | número decimal (aceita `3,5`) | `float`, ou `None` se vazio |
| `"bool"` | caixa de seleção | `True` / `False` |
| `"choice"` | lista de opções | um dos itens de `options` |
| `"file"` | caminho + botão Procurar… | `str`, ou `None` se vazio |
| `"folder"` | caminho + botão Procurar… | `str`, ou `None` se vazio |

## Argumentos

O tipo é o **único** argumento posicional. Todos os outros são nomeados.

| Argumento | Para que serve | Padrão |
| :-- | :-- | :-- |
| `default` | valor inicial e valor usado na linha de comando | `None` |
| `label` | rótulo do campo | nome da variável |
| `help` | texto de ajuda abaixo do campo | — |
| `required` | campo obrigatório (`*`); bloqueia Executar se vazio | `False` |
| `group` | cartão onde o campo aparece | `"Geral"` |
| `options` | lista de opções (obrigatório em `choice`) | — |
| `filetypes` | filtro do Procurar…, ex.: `[("CSV", "*.csv"), ("Excel", "*.xlsx")]` | — |
| `save` | `file` de **saída**: abre "Salvar como" e não exige que o arquivo exista | `False` |
| `must_exist` | exige que o arquivo/pasta exista | `True` (ou `False` se `save=True`) |
| `min` / `max` | limites para `int` e `float` | — |
| `aliases` | nomes antigos do parâmetro, para não perder valores salvos ao renomear | `[]` |

Um argumento desconhecido gera **aviso** (não impede a execução).

## Regras (o app mostra erro se forem quebradas)

1. **Só no nível do módulo**, no formato `NOME = param(...)`. Nada de `param()` dentro de função, `if`, `for`, `with` ou em atribuição múltipla.
2. **Só valores literais**: texto, número, `True`/`False`, `None` e listas/tuplas desses. Isto **não** vale:
   ```python
   BASE = r"C:\dados"
   PASTA = param("folder", default=BASE + r"\entrada")   # erro: não é literal
   ```
   Escreva o valor por extenso: `default=r"C:\dados\entrada"`.
3. Cada nome aparece uma vez só.
4. O `default` precisa combinar com o tipo (ex.: `int` → número inteiro) e, em `choice`, estar em `options`.
5. Uma chamada por atribuição; a chamada pode ocupar várias linhas.

## Passo a passo para converter um script com valores fixos

1. **Localize** as variáveis que você costuma editar antes de rodar (caminhos, datas, limites, opções).
2. **Mova-as para o topo** do arquivo, logo depois dos `import`, fora de qualquer função.
3. **Troque** cada `X = valor` por `X = param("tipo", default=valor, label="...")`:
   ```python
   # antes
   PASTA = r"C:\dados\jan"
   LIMITE = 500
   # depois
   PASTA = param("folder", default=r"C:\dados\jan", label="Pasta de entrada", required=True)
   LIMITE = param("int", default=500, label="Máximo de linhas", min=1)
   ```
4. **Acrescente** `from psr import param` e uma docstring no início explicando o que o script faz.
5. Se o script usa `input()`, troque por um `param()` — no RunPython o teclado fica fechado e `input()` falha.
6. **Carregue no RunPython** (botão **+**) e confira se os campos aparecem sem erro.
7. Rode uma vez pelo app e uma vez pela linha de comando (na pasta dos scripts) para confirmar.

## Erros comuns e o que o app mostra

| Situação | Mensagem |
| :-- | :-- |
| `default=VARIAVEL` | "o valor de default precisa ser literal…" |
| `param()` dentro de `if`/função | "param() só pode ser usado no nível do módulo…" |
| tipo errado, ex.: `"date"` | "tipo desconhecido 'date'…" |
| `choice` sem `options` | "o tipo "choice" exige options=[...]" |
| esqueceu o import | aviso: "falta 'from psr import param' no script" |
| erro de sintaxe no script | "erro de sintaxe: …" com a linha |

## Limitações conhecidas (v1)

- O RunPython mostra **só os scripts carregados** pelo botão **+** (outros `.py` na pasta são ignorados). Ao carregar, o script é copiado para a pasta de scripts. **Remover da lista** (lixeira ou botão direito) não apaga o arquivo.
- **Recarregar scripts** (F5) relê só os scripts carregados.
- Os valores salvos ficam ligados ao **nome do arquivo**. Renomear o script perde os últimos valores.
- O script roda com a pasta de trabalho igual à pasta dos scripts.
- `input()` não funciona (o teclado fica fechado e o script recebe fim de arquivo).
- Uma execução por vez.
