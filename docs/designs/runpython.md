# Python Script Runner (RunPython)

*   **Autor:** flavio.lp@gmail.com
*   **Status:** Proposed
*   **Data:** 2026-11-02

--------------------------------------------------------------------------------

## Visão geral

O RunPython é um app desktop para Windows. Ele roda scripts Python sem que a pessoa precise abrir o código ou usar a linha de comando. Funciona assim:

1. O app lê uma pasta local de scripts e mostra a lista numa barra lateral.
2. Ao selecionar um script, o app lê o arquivo **sem executá-lo** e encontra as linhas `param(...)`, que marcam os parâmetros.
3. Para cada parâmetro, monta um campo no formulário: texto, número, caixa de seleção, lista de opções, arquivo ou pasta. Os campos ficam organizados em grupos.
4. O usuário preenche os campos e clica em **Executar**.
5. O app roda o script no Python já instalado na máquina, mostra a saída ao vivo e permite **abortar** a execução.

Os valores informados chegam ao script por um arquivo JSON temporário. Dentro do script, um módulo auxiliar pequeno (`psr.py`) lê esse arquivo. Antes de cada execução, o app verifica se o `psr.py` está na pasta dos scripts, na versão certa, e o copia para lá se faltar. Como o Python sempre procura módulos na pasta do próprio script, o mesmo script também roda pela linha de comando, usando os valores padrão.

Tudo é local. Cada pessoa usa o app na própria máquina, com um único ambiente Python compartilhado por todos os scripts. O app é escrito em Python com Tkinter/ttk e o tema sv-ttk, e roda no Python do próprio usuário.

## O problema

Hoje os scripts rodam pela linha de comando, e os valores de entrada (pastas, arquivos, limites, opções) ficam **fixos no código**. Para rodar com outros valores, alguém precisa abrir o `.py`, achar a variável certa, editar, salvar e rodar no terminal. Isso causa três problemas:

*   **Só quem entende Python consegue usar.** Quem não é técnico não sabe qual variável mudar, pode quebrar a sintaxe do arquivo e não entende a saída do terminal.
*   **Erros silenciosos.** Um caminho digitado errado ou um valor esquecido de uma execução anterior só aparece quando o script falha no meio. Nada valida a entrada antes.
*   **Nada fica registrado.** Não há histórico de quais valores foram usados, se a execução deu certo ou qual foi o erro.

A proposta é marcar no próprio script quais variáveis são parâmetros, com nome, tipo, ajuda e valor padrão. O app usa essa marcação para gerar a tela automaticamente. Um script novo ou alterado não exige mudar o app.

## Objetivos

*   **G1. Rodar sem editar código.** Qualquer script com marcadores `param(...)` válidos pode ser executado pelo formulário, sem abrir o `.py`.
*   **G2. Descobrir parâmetros sem executar.** O app encontra os parâmetros só lendo o texto do script. Abrir ou selecionar um script nunca roda código dele.
*   **G3. Tela gerada a partir do script.** Cada parâmetro vira um campo com rótulo, ajuda, valor padrão, marca de obrigatório e grupo. Os tipos da v1 são:
    *   texto;
    *   inteiro;
    *   decimal (aceita vírgula);
    *   sim/não;
    *   lista de opções;
    *   arquivo, com filtro de extensão;
    *   pasta.
*   **G4. Validação antes de rodar.** Campo obrigatório vazio, número inválido ou arquivo inexistente mostra o erro ao lado do campo e bloqueia o botão Executar.
*   **G5. Execução visível e controlável.** O log aparece ao vivo e a execução termina num de quatro estados: **sucesso**, **falhou**, **parado por você** ou **não iniciou**. O botão Abortar encerra o script e todos os processos que ele abriu.
*   **G6. Erros compreensíveis.** Pacote faltando aparece como "Falta o pacote X", com o comando `pip install` pronto para copiar. Python ausente ou marcador mal escrito também aparecem com mensagem clara, e o app não fecha.
*   **G7. Acompanhar mudanças no script.** Ao abrir o app ou recarregar a lista, scripts alterados são relidos e a tela se ajusta:
    *   parâmetros novos aparecem;
    *   os removidos ou renomeados seguem as regras de valores salvos.
*   **G8. Lembrar os últimos valores.** Cada script reabre com os valores da última execução. O botão Restaurar padrões volta aos valores do código.
*   **G9. Scripts continuam independentes.** Um script convertido roda pela linha de comando com os valores padrão, sem o app aberto.
*   **G10. Helper sempre disponível.** Antes de executar, o app confere se o `psr.py` está na pasta dos scripts e na versão esperada. Se não estiver, o app copia ou atualiza o arquivo sozinho e registra isso no log.
*   **G12. Adicionar script.** O botão "+ Adicionar script" copia um `.py` escolhido pelo usuário para a pasta de scripts. Antes de sobrescrever um arquivo com o mesmo nome, o app pergunta.
*   **G11. Formato documentado.** Um documento `MARKER_SPEC.md` descreve o formato dos marcadores, com exemplos e um passo a passo para converter scripts com valores fixos.

## Não-objetivos

*   **`skill.md` para o assistente de IA.** Os scripts serão convertidos e escritos seguindo o `MARKER_SPEC.md`.
*   **Agendamento** de execuções, terminal de comandos global, webhooks e notificações.
*   **Perfis de usuário, login** ou permissões.
*   **Rede:** pasta compartilhada, execução remota ou servidor.
*   **Um ambiente virtual (venv) por script.** Todos usam o mesmo Python.
*   **Instalar pacotes que os scripts usam.** O app só mostra o comando. A instalação automática vale apenas para o `psr.py`.
*   **Na v1:**
    *   vários scripts rodando ao mesmo tempo;
    *   presets com nome;
    *   tipos data e senha;
    *   monitorar a pasta em tempo real;
    *   instalador `.exe` empacotado.
*   **Visual idêntico ao mockup do Stitch.** O layout segue o mockup: barra lateral, grupos em cartões e barra de execução. O acabamento é o do tema Tkinter.

## Perguntas em aberto

*   **Scripts atuais.** Algum script usa `input()` ou caminhos relativos à pasta do script? A proposta é rodar com a pasta de trabalho igual à pasta do script e com a entrada do teclado fechada.
*   **Instalação do Python nas máquinas.** O Python veio do python.org, da Microsoft Store ou do conda? O Tkinter está incluído? O app checa isso ao abrir, mas a resposta muda o que o app precisa suportar.

## Jornadas críticas do usuário (CUJs)

### CUJ 1: Rodar um script pela primeira vez

*   **Dado** que o app está aberto, a pasta de scripts está configurada e contém `relatorio.py` com três `param(...)` válidos.
*   **Quando** o usuário seleciona `relatorio.py`, preenche a pasta de entrada e clica em Executar.
*   **Então** o app:
    *   valida os campos;
    *   confirma que o `psr.py` está instalado e instala se precisar;
    *   roda o script;
    *   mostra a saída ao vivo;
    *   termina com o estado **sucesso** e o tempo de execução;
    *   salva os valores usados para a próxima vez.

### CUJ 2: Script atualizado com parâmetro novo

*   **Dado** que `relatorio.py` já foi executado e tem valores salvos, e o autor acrescentou um parâmetro obrigatório `FORMATO` e renomeou `PASTA` para `PASTA_ENTRADA` com `aliases=["PASTA"]`.
*   **Quando** o usuário abre o app e seleciona o script.
*   **Então**:
    *   o campo `FORMATO` aparece vazio e marcado como obrigatório, e o botão Executar fica bloqueado até ser preenchido;
    *   `PASTA_ENTRADA` já vem preenchido com o valor salvo de `PASTA`.

### CUJ 3: Script falha por pacote faltando

*   **Dado** um script que importa `pandas`, que não está instalado.
*   **Quando** o usuário executa.
*   **Então** a execução termina como **falhou** e o app mostra "Falta o pacote pandas", com o comando `pip install pandas` e um botão para copiar. O log completo fica disponível, recolhido.

### CUJ 4: Abortar uma execução longa

*   **Dado** um script em execução que abriu processos filhos (por exemplo, `multiprocessing`).
*   **Quando** o usuário clica em Abortar.
*   **Então** o script e todos os processos filhos são encerrados, e a execução termina como **parado por você**. Nenhum processo `python.exe` desse script fica rodando.

### CUJ 5: Script com marcador mal escrito

*   **Dado** um script com `param("int", default=abc)`, que não é um valor literal.
*   **Quando** o app lê a pasta.
*   **Então** o script aparece na lista com um selo de erro. Ao selecioná-lo, o app mostra a linha e o motivo do erro, em vez do formulário. O app continua funcionando normalmente.

## Plano técnico (arquitetura)

### Visão dos componentes

O app é um programa Python (`RunPython.pyw`) que roda no Python do próprio usuário (versão 3.9 ou mais nova, com Tkinter). Ele tem duas partes:

*   **Interface (Tkinter/ttk + sv-ttk):** barra lateral, formulário, barra de execução e painel de log.
*   **Núcleo (sem interface, testável):**
    *   leitor de marcadores;
    *   validação;
    *   armazenamento de valores;
    *   executor de processos;
    *   instalação do helper.

O `psr.py` é **um único arquivo** que tem duas funções:

1. **Dentro do script do usuário:** fornece `param()`, que devolve o valor vindo do app ou o valor padrão.
2. **Dentro do app:** fornece `scan_file()`, o leitor de marcadores.

O app importa a cópia do `psr.py` que vem com ele. Assim, o app e os scripts usam **o mesmo código** para ler os marcadores, e as duas leituras nunca divergem.

```text
                         ┌───────────────────────────────────────────┐
                         │             RunPython.pyw (Tk)            │
                         │  Barra lateral │ Formulário │ Log ao vivo │
                         └───────┬───────────────┬───────────┬───────┘
                                 │               │           │
      ┌──────────────────────────▼──┐  ┌─────────▼───────┐  ┌▼──────────────────────┐
      │ scanner: lista os .py       │  │ validação +     │  │ runner: Popen + Job    │
      │ da pasta, guarda data de    │  │ valores salvos  │  │ Object, 2 threads de   │
      │ alteração, chama            │  │ (%APPDATA%)     │  │ leitura → fila → Tk    │
      │ psr.scan_file()             │  └────────┬────────┘  └──┬──────────────┬──────┘
      └──────────────┬──────────────┘           │              │              │
                     │ lê o texto (ast),        │ grava JSON   │ inicia       │ stdout/stderr
                     │ nunca executa            ▼ temporário   ▼              │
      ┌──────────────▼──────────────┐  %TEMP%\psr_xxx.json   python.exe -u script.py
      │ Pasta de scripts            │           ▲              (cwd = pasta dos scripts,
      │  relatorio.py               │           │ PSR_PARAMS_FILE  stdin fechado)
      │  backup.py                  │           └────────────────┤
      │  psr.py  ← copiado pelo app │◄── from psr import param ──┘
      └─────────────────────────────┘
```

### 1. Formato do marcador (contrato do script)

Um script convertido fica assim:

```python
"""Gera o relatório mensal a partir das planilhas de entrada."""   # vira a descrição na tela
# psr-format: 1
from psr import param

PASTA   = param("folder", default=r"C:\dados", label="Pasta de entrada",
                group="Arquivos", required=True)
SAIDA   = param("file", default="saida.csv", label="Arquivo de saída",
                filetypes=[("CSV", "*.csv")], save=True, group="Arquivos")
LIMITE  = param("int", default=1000, label="Máximo de linhas", min=1, group="Execução")
FORMATO = param("choice", default="csv", options=["csv", "xlsx"], group="Execução")
SIMULAR = param("bool", default=False, label="Só simular", help="Não grava nada.")
```

**Regras que o leitor aplica:**

*   Só valem atribuições **no nível do módulo**, no formato `NOME = param(...)`. Uma chamada `param()` dentro de função, `if` ou laço gera erro de marcador. O motivo: o app não consegue prever se o código vai passar por ali.
*   **Todos os argumentos precisam ser literais:** texto, número, `True`/`False`, `None` e listas ou tuplas de literais. O leitor usa `ast.literal_eval`, então variáveis ou expressões no lugar desses valores geram erro de marcador.
*   **Primeiro argumento (tipo):** `text`, `int`, `float`, `bool`, `choice`, `file` ou `folder`. Qualquer outro gera erro.
*   **Argumentos nomeados:**

    | Argumento | Para que serve |
    | :-- | :-- |
    | `default` | Valor padrão. |
    | `label` | Rótulo do campo. Se faltar, o app usa o nome da variável. |
    | `help` | Texto de ajuda abaixo do campo. |
    | `required` | Marca o campo como obrigatório. |
    | `group` | Cartão em que o campo aparece. Sem ele, o campo vai para o cartão "Geral". |
    | `options` | Opções da lista (`choice`). |
    | `filetypes` | Filtro de extensão (`file`). |
    | `save` | `file` de saída: abre "Salvar como" e não exige que o arquivo exista. |
    | `must_exist` | Exige que o arquivo ou pasta exista (padrão `True`, exceto quando `save=True`). |
    | `min` / `max` | Limites para `int` e `float`. |
    | `aliases` | Nomes antigos do parâmetro, para recuperar valores salvos. |

*   Um argumento nomeado desconhecido gera **aviso, não erro**. Assim, um script feito para uma versão futura ainda abre.
*   `# psr-format: N` é opcional. Se faltar, vale 1. Se `N` for maior que o suportado pelo app, o script fica com selo de erro: "feito para uma versão mais nova do RunPython".
*   A descrição na tela é a docstring do módulo. O título é o nome do arquivo.
*   Um script **sem nenhum `param()`** aparece na lista normalmente, com o aviso "sem parâmetros", e pode ser executado.

### 2. Como `param()` recebe o valor na execução

1.  Na primeira chamada, `param()` lê a variável de ambiente `PSR_PARAMS_FILE`.
    *   Se ela **não existir** (execução pela linha de comando), cada `param()` devolve o seu `default`.
2.  Se existir, `param()` carrega o JSON uma única vez. O formato é:
    ```text
    {"format": 1, "script": "relatorio.py", "values": {"PASTA": "D:\\x", "LIMITE": 500, ...}}
    ```
3.  Para saber o nome da variável que está sendo atribuída, `param()` lê o próprio arquivo do script com o mesmo `scan_file()` usado pelo app. A leitura é feita uma vez e guardada.
    *   O resultado associa a **faixa de linhas** de cada chamada `param()` ao nome da variável.
    *   A linha atual de quem chamou (`sys._getframe(1).f_lineno`) cai dentro de uma única faixa. Isso funciona mesmo com chamadas que ocupam várias linhas, porque as chamadas não podem ser aninhadas.
4.  `param()` devolve o valor do JSON, que já vem no tipo certo. Se a chave não estiver no JSON, devolve o `default`.
5.  Processos filhos (`multiprocessing`) herdam a variável de ambiente e, ao reimportar o script, recebem os mesmos valores.

### 3. Leitura da pasta e detecção de mudanças

*   A pasta de scripts é escolhida na primeira abertura e guardada nas configurações. O padrão sugerido é `Documentos\RunPython\scripts`.
*   O app lista os arquivos `*.py` **só do primeiro nível** da pasta. Ficam de fora:
    *   o `psr.py`;
    *   arquivos que começam com `_`.
*   Para cada script, o app guarda a data de alteração e o resultado da leitura. Ele relê o script quando:
    *   o app abre;
    *   o usuário clica em **Recarregar**;
    *   o usuário seleciona um script cuja data de alteração mudou;
    *   **imediatamente antes de executar**. Se os parâmetros mudaram desde que o formulário foi montado, o app atualiza a tela, mostra "O script mudou, confira os campos" e **não executa**.
*   Um arquivo que não pode ser lido (erro de sintaxe ou de codificação) fica na lista com selo de erro, mostrando a linha e o motivo.

### 4. Valores salvos e mudanças no script

*   **Onde ficam:**
    *   `%APPDATA%\RunPython\values\<nome-do-script>.json`;
    *   formato: `{"format": 1, "values": {...}, "orphans": {...}, "updated": "..."}`;
    *   gravação atômica: escreve um arquivo temporário e troca com `os.replace`.
*   **Identificação do script:** é feita pelo **nome do arquivo**. Se o script for renomeado, os valores salvos se perdem. Isso fica documentado.
*   **Ao montar o formulário**, o app junta os valores salvos com os parâmetros atuais:

    | Situação | Comportamento |
    | :-- | :-- |
    | Parâmetro novo | Usa o `default`. Se for obrigatório e não tiver padrão, o campo fica vazio e o botão Executar fica bloqueado. |
    | Parâmetro renomeado | Busca o valor pelo nome atual e depois por cada nome em `aliases`. |
    | Parâmetro removido | O valor vai para `orphans`, com uma nota discreta "1 valor antigo não é mais usado". |
    | Tipo mudou | Tenta converter (por exemplo, `"10"` para inteiro). Se não der, usa o `default` e avisa. |
    | Opção sumiu da lista | Usa o `default`. |

*   Os valores só são salvos **depois que a execução inicia**, para guardar o que de fato foi usado.

### 5. Validação

*   **Texto:** se `required`, não pode ficar vazio.
*   **Inteiro:** aceita o sinal de menos e respeita `min` e `max`. Não aceita "1,5".
*   **Decimal:** aceita "3,5" e "3.5", e respeita `min` e `max`.
*   **Arquivo / pasta:** confere se existe, conforme `must_exist`.
*   **Lista de opções:** o valor precisa estar em `options`.
*   O erro aparece em vermelho embaixo do campo. O botão Executar fica desativado enquanto houver erro.

### 6. Execução

1.  **Python:** é o mesmo que roda o app. O app usa o `python.exe` ao lado do `pythonw.exe`. Nas Configurações dá para escolher outro executável, e o app testa a escolha com `-c "import sys; print(sys.version)"`.
2.  **Helper:** o app lê o `PSR_VERSION` do `psr.py` na pasta dos scripts, só lendo o texto, sem executar.
    *   Se o arquivo não existir ou a versão for diferente da que vem com o app, o app copia a sua versão: grava um arquivo temporário e troca com `os.replace`. Isso aparece no log como "psr.py atualizado para X".
    *   Se a cópia falhar (por exemplo, pasta sem permissão), a execução termina como **não iniciou**, com o motivo.
3.  **Valores:** o app grava o JSON em `%TEMP%\psr_<aleatório>.json` e apaga o arquivo no fim da execução, inclusive se ela falhar ou for abortada.
4.  **Processo:**
    ```text
    Popen([python, "-u", script],
          cwd=pasta_dos_scripts,
          stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
          creationflags=CREATE_NO_WINDOW,
          env = ambiente atual + PSR_PARAMS_FILE + PYTHONIOENCODING=utf-8
                + PYTHONPATH = pasta_dos_scripts (prefixado))
    ```
    Nunca usa `shell=True`. Os argumentos são passados como lista.
5.  **Job Object (Windows):** logo após iniciar, o app coloca o processo num Job Object com a opção "matar tudo ao fechar" (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), usando `ctypes`, sem dependências externas.
    *   **Abortar** chama `TerminateJobObject` e encerra o script e todos os filhos.
    *   Se o app fechar, o Windows encerra o job.
    *   **Limitação conhecida:** existe uma janela de milissegundos entre iniciar o processo e colocá-lo no job. Um script que abre processos filhos na primeira instrução pode escapar. Isso fica documentado.
6.  **Log ao vivo:**
    *   Duas threads leem stdout e stderr linha a linha e colocam numa fila.
    *   A interface esvazia a fila a cada 50 ms e insere as linhas **em lote**.
    *   stderr aparece em vermelho.
    *   O painel mostra no máximo 10.000 linhas; o arquivo de log guarda tudo.
7.  **Estado final:**

    | Estado | Quando |
    | :-- | :-- |
    | Sucesso | Código de saída 0. |
    | Falhou | Código diferente de 0. |
    | Parado por você | O usuário clicou em Abortar. |
    | Não iniciou | Erro antes do processo começar: Python inválido, cópia do helper falhou ou validação. |

    A barra de execução mostra o estado, a duração e o código de saída.
8.  **Dicas de erro:** o app procura no stderr a linha `ModuleNotFoundError: No module named 'X'`.
    *   Se encontrar, mostra um aviso "Falta o pacote X" com o comando `"<python>" -m pip install <pacote>` e o botão **Copiar**.
    *   Uma tabela pequena traduz nomes de módulo para nomes de pacote:

        | Módulo | Pacote |
        | :-- | :-- |
        | `cv2` | `opencv-python` |
        | `PIL` | `Pillow` |
        | `sklearn` | `scikit-learn` |
        | `yaml` | `PyYAML` |
        | `bs4` | `beautifulsoup4` |
        | `win32api` | `pywin32` |
        | `dotenv` | `python-dotenv` |

9.  **Uma execução por vez:** enquanto um script roda, o botão Executar dos outros scripts fica desativado. Ao tentar fechar o app durante uma execução, ele pergunta "Abortar e sair?".

### 7. Registro de execuções e diagnóstico

*   **Log por execução:** `%APPDATA%\RunPython\logs\<script>\<AAAAMMDD-HHMMSS>.log`.
    *   Cabeçalho com o Python usado, a versão do `psr.py`, os valores, o código de saída e a duração.
    *   O app guarda as **20 últimas** execuções de cada script e apaga as mais antigas.
*   **Log do próprio app:** `%APPDATA%\RunPython\app.log`, com rotação de 1 MB e 3 arquivos.
    *   Registra erros de leitura, cópia do helper e exceções da interface.
*   **Botões do painel de log:**
    *   **Copiar log**;
    *   **Salvar log**;
    *   **Abrir pasta do script**;
    *   **Copiar diagnóstico**, que copia a versão do app, do Python e do `psr.py` e o caminho da pasta.
*   Uma **exceção não tratada** na interface é registrada no `app.log` e mostrada numa caixa de diálogo, sem fechar o app.

### 8. Interface

O layout segue o mockup do Stitch, com textos em português. O tema claro ou escuro segue o Windows e pode ser trocado nas Configurações.

*   **Barra lateral (esquerda):**
    *   nome do app;
    *   botão **+ Adicionar script**;
    *   campo de busca, que filtra pelo nome;
    *   lista de scripts. Cada item tem o nome e uma linha de status: "Pronto", "Executando…", "Última execução: há 2 h — sucesso", "Erro de marcador" ou "Sem parâmetros";
    *   no rodapé: **Abrir pasta**, **Recarregar** e **Configurações**.
*   **Área principal (direita):**
    *   **Cabeçalho:** nome do script, caminho e descrição (docstring), com o botão **Restaurar padrões**.
    *   **Formulário com rolagem:** um cartão (`ttk.Labelframe`) por `group`, na ordem em que os grupos aparecem no script. Os campos ficam numa grade de 1 ou 2 colunas, conforme a largura da janela. Caixas de seleção ocupam uma linha cada, com a ajuda embaixo.
    *   **Barra de execução:** texto de estado e botão **Executar**, que vira **Abortar** durante a execução.
    *   **Painel de log:** abaixo, com divisor arrastável. Fica recolhido até a primeira execução.
*   **Campos por tipo:**

    | Tipo | Campo |
    | :-- | :-- |
    | `text` | Entrada de texto. |
    | `int` / `float` | Entrada com validação. |
    | `bool` | Caixa de seleção. |
    | `choice` | Lista (`Combobox`) só para leitura. |
    | `file` | Entrada + botão **Procurar…** (`askopenfilename`, ou `asksaveasfilename` quando `save=True`). |
    | `folder` | Entrada + botão **Procurar…** (`askdirectory`). |

*   **Escala da tela:** o app ativa o modo de DPI por monitor (`SetProcessDpiAwareness`) para não ficar borrado em telas com escala.
*   **Primeira abertura:**
    *   confere se o Tkinter funciona. Se não funcionar, mostra uma mensagem pela API do Windows (`MessageBoxW`);
    *   pede a pasta de scripts.
*   **+ Adicionar script:**
    *   abre o seletor de `.py` e copia o arquivo para a pasta de scripts;
    *   se já existir um arquivo com o mesmo nome, pergunta antes de sobrescrever;
    *   depois relê a pasta e seleciona o script adicionado.

### 9. Configurações

`%APPDATA%\RunPython\config.json`, que guarda:

*   a pasta de scripts;
*   o Python escolhido (vazio = o mesmo do app);
*   o tema;
*   o tamanho e a posição da janela;
*   o último script selecionado.

### Segurança

*   **Selecionar ou listar um script nunca executa o código dele.** O app só usa `ast.parse` e `ast.literal_eval`. Um teste automatizado garante isso: lê um script que criaria um arquivo se fosse executado e confere que o arquivo não foi criado.
*   Execução sem shell, com a lista de argumentos.
*   O JSON de valores é apagado no fim de toda execução.
*   O app não instala pacotes de terceiros. A única escrita fora de `%APPDATA%` é o `psr.py` na pasta dos scripts e a cópia feita por "+ Adicionar script".

## Alternativas consideradas

### Usar o Gooey em vez de construir o app

*   **Prós:** já existe e transforma um `argparse` em janela com uma linha (`@Gooey`). Tem seletores de arquivo e pasta prontos.
*   **Contras:**
    *   praticamente sem manutenção desde cerca de 2021;
    *   depende do wxPython, que às vezes não tem instalador pronto para versões novas do Python;
    *   é uma janela por script, sem lista central, sem valores salvos entre execuções e sem Abortar que encerre os processos filhos.
*   **Motivo da rejeição:** não atende à lista de scripts, à atualização da tela quando o script muda, nem ao público não técnico, que precisa de um único lugar para encontrar e rodar os scripts.

### Marcador em comentário (`PASTA = r"C:\dados"  # @param tipo=pasta ...`)

*   **Prós:** é a mudança mínima nos scripts atuais. A linha original fica igual, só ganha um comentário.
*   **Contras:**
    *   o módulo `ast` descarta comentários, então seria preciso um segundo leitor baseado em texto (`tokenize`) e uma mini-linguagem própria para `chave=valor` com aspas e listas;
    *   o mais grave: a linha `PASTA = r"C:\dados"` sobrescreve qualquer valor injetado antes, então ainda faltaria um jeito de entregar o valor ao script.
*   **Motivo da rejeição:** resolve só a descoberta dos parâmetros e não a entrega dos valores. Ficou como segunda opção.

### `argparse` (parâmetros pela linha de comando)

*   **Prós:** é o padrão do Python, documentado e conhecido. O script continua natural na linha de comando (`--pasta X`).
*   **Contras:**
    *   ler os `add_argument` só pelo texto é frágil, porque os argumentos costumam vir de variáveis, laços e funções;
    *   a alternativa, rodar o script com uma opção que exporta a lista de parâmetros, **executa código do script** só para montar a tela;
    *   a linha de comando tem problemas de aspas e limite de tamanho.
*   **Motivo da rejeição:** contraria o objetivo G2 (descobrir sem executar).

### Bloco de metadados YAML/JSON no topo do script

*   **Prós:** fica tudo num lugar só e é fácil de ler.
*   **Contras:**
    *   YAML não vem com o Python, e JSON dentro de comentário é desconfortável de escrever;
    *   a definição fica longe da variável que ela controla, e as duas tendem a ficar diferentes com o tempo;
    *   continua sem resolver a entrega dos valores.
*   **Motivo da rejeição:** mais manutenção para o autor do script, sem ganho sobre `param()`.

### Streamlit / NiceGUI (interface no navegador)

*   **Prós:** formulários fáceis de montar e visual moderno.
*   **Contras:**
    *   sobem um servidor local e abrem o navegador;
    *   execuções longas, log ao vivo e Abortar ficam difíceis de controlar;
    *   exigem instalar pacotes grandes.
*   **Motivo da rejeição:** pesados para um app local e frágeis para o controle de processos.

### PySide6 / Qt

*   **Prós:** interface fluida, visual nativo e componentes ricos.
*   **Contras:** entre 60 e 200 MB de dependência, instalada no Python compartilhado com os scripts. Pode entrar em conflito com versões de pacotes que os scripts usam.
*   **Motivo da rejeição:** o pedido era a opção mais leve. O Tkinter já vem com o Python.

### C# WPF / WinForms

*   **Prós:** totalmente nativo do Windows, rápido, e gera um `.exe` próprio.
*   **Contras:**
    *   uma segunda linguagem para manter;
    *   não reaproveita o leitor de marcadores em Python, então seriam dois leitores que podem divergir;
    *   precisa do runtime .NET ou de um executável maior.
*   **Motivo da rejeição:** a duplicação do leitor contraria a decisão de usar um único `psr.py` para o app e para os scripts.

### Tauri (WebView2)

*   **Prós:** executável pequeno, usa o navegador embutido do Windows 11 e permite reproduzir o mockup do Stitch quase exatamente.
*   **Contras:**
    *   o build exige Rust e Node;
    *   o núcleo em Python teria de rodar como processo auxiliar, o que dá mais peças para manter.
*   **Motivo da rejeição:** o visual idêntico ao mockup foi declarado não-objetivo. Fica como caminho futuro, se o visual passar a ser exigência.

### Electron

*   **Prós:** visual web livre e ecossistema grande.
*   **Contras:** mais de 100 MB e alto uso de memória.
*   **Motivo da rejeição:** contraria o requisito de leveza.

### Instalar o `psr.py` na pasta de pacotes do usuário (user site-packages)

*   **Prós:** o import funciona para scripts em qualquer pasta, e não precisa de pip nem de administrador.
*   **Contras:**
    *   falha em venv/conda com essa pasta desativada;
    *   com vários Pythons instalados, o `python` usado no terminal pode não enxergar o arquivo.
*   **Motivo da rejeição:** escolha do responsável pelo projeto. A opção C funciona com qualquer Python.

### `pip install --user` de um pacote local

*   **Prós:** é a instalação padrão do Python, dá para desinstalar, e a versão é clara (`pip show`).
*   **Contras:**
    *   precisa de pip;
    *   venv/conda recusam `--user`;
    *   a primeira execução fica mais lenta;
    *   os mesmos problemas com vários Pythons.
*   **Motivo da rejeição:** escolha do responsável pelo projeto, pelas mesmas razões da opção anterior.

### Localizar o Python automaticamente (`py -0p` → registro → PATH)

*   **Prós:** encontra o Python "principal" da máquina mesmo que o app tenha sido aberto com outro.
*   **Contras:**
    *   exige mais código;
    *   precisa detectar e descartar o `python.exe` falso da Microsoft Store, que só abre a loja;
    *   o leitor do app e os scripts podem acabar em Pythons diferentes.
*   **Motivo da rejeição:** o responsável pelo projeto decidiu usar o mesmo Python que roda o app, com opção de trocar nas Configurações.

### Só ler a pasta, sem o botão "+ Adicionar script"

*   **Prós:** menos código e nenhuma escrita além do `psr.py`.
*   **Contras:** o usuário não técnico precisaria saber onde fica a pasta e copiar o arquivo pelo Explorer.
*   **Motivo da rejeição:** escolha do responsável pelo projeto, para facilitar a vida de quem não é técnico.

--------------------------------------------------------------------------------

## Requisitos não funcionais

*   **Compatibilidade:**
    *   Windows 10 e 11;
    *   Python 3.9 a 3.13, de python.org ou Microsoft Store. Conda funciona se tiver Tkinter;
    *   o app e o `psr.py` usam **só a biblioteca padrão**;
    *   o tema sv-ttk vai **embutido** no app (`vendor/`, licença MIT), para cumprir "nada a instalar".
*   **Desempenho:**
    *   ler uma pasta com 200 scripts: menos de 1 s;
    *   abrir um script e montar o formulário: menos de 200 ms;
    *   um script que imprime 10.000 linhas por segundo não pode travar a interface (o painel atualiza em lotes a cada 50 ms);
    *   o app parado usa menos de 60 MB de memória.
*   **Segurança:** ver a subseção Segurança do Plano técnico.
*   **Atualização do app:**
    *   para atualizar, basta substituir a pasta do app;
    *   o `psr.py` dos scripts é atualizado sozinho na próxima execução;
    *   os dados em `%APPDATA%` têm um campo `format` para permitir migração futura;
    *   **volta para versão anterior:** um `psr.py` mais novo continua lendo marcadores `psr-format: 1`, porque o formato só cresce com argumentos opcionais.

### Recursos adicionais

*   [concepts_brief.md](../concepts_brief.md): resumo do brainstorm e revisão com 6 lentes.
*   [docs/Brefing.txt](../Brefing.txt): pedido original.
*   Mockup "Python Script Runner" no Stitch (projeto "Dynamic Python Script Runner").

### Melhorias futuras

*   **Presets com nome**, por exemplo "Fechamento mensal" e "Teste rápido".
*   **Tipos `date` e `password`.** O tipo senha exige não gravar o valor em lugar nenhum e mascarar no log.
*   **Monitorar a pasta em tempo real**, em vez de reler só ao abrir ou recarregar.
*   **Vários scripts rodando ao mesmo tempo**, com um painel de log por execução.
*   **Subpastas** na pasta de scripts, cada uma com a própria cópia do `psr.py`.
*   **Instalador `.exe`** ou atalho no menu Iniciar.
*   **Interface Tauri** reproduzindo o mockup do Stitch, reaproveitando o `psr.py`.

--------------------------------------------------------------------------------

## Plano de implementação detalhado

### Estrutura final do projeto

```text
RunPython/
├── RunPython.pyw
├── pyproject.toml
├── README.md
├── .gitignore
├── docs/
│   └── MARKER_SPEC.md
├── examples/
│   └── exemplo_relatorio.py
├── runpython/
│   ├── __init__.py
│   ├── psr.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── paths.py
│   │   ├── config.py
│   │   ├── applog.py
│   │   ├── scanner.py
│   │   ├── validation.py
│   │   ├── values_store.py
│   │   ├── helper_install.py
│   │   ├── python_env.py
│   │   ├── winjob.py
│   │   ├── runner.py
│   │   ├── error_hints.py
│   │   └── run_log.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py
│   │   ├── app.py
│   │   ├── sidebar.py
│   │   ├── form.py
│   │   ├── fields.py
│   │   ├── runbar.py
│   │   ├── log_panel.py
│   │   └── settings_dialog.py
│   └── vendor/
│       └── sv_ttk/            (cópia do sv-ttk + LICENSE)
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── markers/           (scripts .py + resultado esperado .json)
    │   └── scripts/           (scripts executáveis para testes do runner)
    ├── test_psr_scan.py
    ├── test_psr_runtime.py
    ├── test_no_execution.py
    ├── test_validation.py
    ├── test_values_store.py
    ├── test_helper_install.py
    ├── test_runner.py
    ├── test_winjob.py
    ├── test_error_hints.py
    └── test_scanner.py
```

### Arquivos a criar

Todos são novos: o projeto não tem código hoje.

#### 1. `runpython/psr.py` (Criar)

*   **Tipo / Escopo:** módulo Python só com a biblioteca padrão. É o **contrato central**: é importado pelo app e copiado para a pasta dos scripts.
*   **Por quê:** um único leitor de marcadores, usado pelo app e pelos scripts, evita que os dois entendam os marcadores de jeitos diferentes.
*   **Conteúdo:**
    *   **Constantes:**
        *   `PSR_VERSION = "1.0.0"`: o app compara esta linha, lida só como texto, com a da sua própria cópia;
        *   `SUPPORTED_FORMAT = 1`;
        *   `KINDS = ("text", "int", "float", "bool", "choice", "file", "folder")`;
        *   `KNOWN_KEYS` = os argumentos nomeados da tabela da seção 1 do Plano técnico.
    *   **`ParamSpec`** (dataclass): `name`, `kind`, `default`, `label`, `help`, `required`, `group`, `options`, `filetypes`, `save`, `must_exist`, `min`, `max`, `aliases`, `lineno`, `end_lineno`.
    *   **`MarkerIssue`** (dataclass): `line`, `message` (em português) e `severity` (`"error"` ou `"warning"`).
    *   **`ScanResult`** (dataclass): `path`, `description` (docstring do módulo ou `""`), `format`, `params: list[ParamSpec]` e `issues: list[MarkerIssue]`. Também tem a propriedade `ok`, verdadeira quando não há nenhum issue de severidade `"error"`.
    *   **`scan_source(text, filename) -> ScanResult`:**
        1.  `ast.parse`. Se der `SyntaxError`, devolve um issue de erro com a linha.
        2.  Lê `# psr-format: N` nas 10 primeiras linhas, com uma regex.
        3.  Percorre `module.body`:
            *   `Assign` com um único alvo `Name`, cujo valor é `Call` para o nome `param` (ou `psr.param`), vira um parâmetro;
            *   `param(...)` em qualquer outro ponto da árvore (`ast.walk`) gera o erro "param() só pode ser usado no nível do módulo".
        4.  Para cada chamada:
            *   o 1º argumento posicional precisa ser um literal de texto dentro de `KINDS`;
            *   cada argumento nomeado passa por `ast.literal_eval`. Se falhar, gera o erro "valor de X precisa ser literal";
            *   uma chave desconhecida gera aviso.
        5.  **Validações cruzadas:**
            *   `choice` exige `options` não vazio;
            *   o `default` precisa ser do tipo do parâmetro e estar em `options`;
            *   `min` precisa ser menor ou igual a `max`;
            *   nomes repetidos geram erro.
        6.  Um `format` maior que `SUPPORTED_FORMAT` gera um erro que bloqueia o script.
    *   **`scan_file(path) -> ScanResult`:** lê os bytes do arquivo, descobre a codificação com `tokenize.detect_encoding` e chama `scan_source`. Um erro de leitura ou de codificação vira um issue.
    *   **`param(kind, **kwargs)`:**
        *   na primeira chamada:
            *   lê `PSR_PARAMS_FILE`. Sem a variável, devolve `kwargs.get("default")`;
            *   carrega o JSON e roda `scan_file` no arquivo de quem chamou (`sys._getframe(1).f_code.co_filename`), guardando o resultado em cache no módulo;
        *   localiza o `ParamSpec` cuja faixa `lineno..end_lineno` contém `sys._getframe(1).f_lineno` e devolve `values.get(nome, default)`;
        *   se não achar a faixa (por exemplo, o arquivo mudou depois de iniciar), devolve o `default` e escreve um aviso no stderr.
    *   **Formato do JSON de valores:** `{"format": 1, "script": "<nome>", "values": {<nome>: <valor já no tipo certo>}}`.

#### 2. `runpython/__init__.py` (Criar)

*   **Tipo / Escopo:** pacote.
*   **Mudanças:** `APP_VERSION = "1.0.0"` e `APP_NAME = "RunPython"`.

#### 3. `RunPython.pyw` (Criar)

*   **Tipo / Escopo:** ponto de entrada (duplo clique abre sem console).
*   **Mudanças:**
    1.  Acrescenta a pasta do app ao `sys.path`.
    2.  Tenta `import tkinter`. Se falhar, mostra `MessageBoxW` via `ctypes`, com a mensagem "Este Python não tem Tkinter. Reinstale pelo python.org marcando 'tcl/tk'", e sai.
    3.  Chama `ui.theme.enable_dpi_awareness()` e depois `ui.app.main()`.
    4.  Envolve tudo num `try` que registra exceções no `app.log`.
*   **Por quê:** garante uma mensagem clara quando falta o Tkinter e evita a janela de console.

#### 4. `runpython/core/paths.py` (Criar)

*   **Tipo / Escopo:** utilitário.
*   **Mudanças:** funções que devolvem e criam as pastas:
    *   `app_data_dir()` → `%APPDATA%\RunPython`;
    *   `values_dir()`;
    *   `logs_dir(script_name)`;
    *   `config_path()`;
    *   `app_log_path()`;
    *   `bundled_psr_path()` → `runpython/psr.py`.

    Também inclui `atomic_write_text(path, text)`, que grava num arquivo temporário na mesma pasta e troca com `os.replace`.
*   **Por quê:** um único lugar para os caminhos e para a gravação atômica, usado por config, valores e helper.

#### 5. `runpython/core/config.py` (Criar)

*   **Tipo / Escopo:** configurações persistentes.
*   **Mudanças:**
    *   `Config` (dataclass): `format=1`, `scripts_dir: str | None`, `python_path: str | None`, `theme: "system" | "light" | "dark"`, `window_geometry: str | None`, `last_script: str | None`;
    *   `load() -> Config`: se o arquivo não existir ou estiver corrompido, devolve o padrão e registra no `app.log`;
    *   `save(cfg)`: usa `atomic_write_text`.

#### 6. `runpython/core/applog.py` (Criar)

*   **Tipo / Escopo:** log do app.
*   **Mudanças:** `setup()` configura o `logging` com `RotatingFileHandler` (1 MB, 3 arquivos) e o formato `data nível módulo mensagem`. Também tem `diagnostics_text(cfg)`, que monta o texto do botão "Copiar diagnóstico": versão do app, do Python, do `psr.py` na pasta, versão do Windows e caminhos.

#### 7. `runpython/core/scanner.py` (Criar)

*   **Tipo / Escopo:** leitura da pasta.
*   **Mudanças:**
    *   `ScriptEntry` (dataclass): `path`, `name`, `mtime`, `scan: ScanResult | None`;
    *   `class ScriptLibrary`:
        *   `__init__(scripts_dir)`;
        *   `refresh() -> list[ScriptEntry]`: lista `*.py` do primeiro nível, sem `psr.py` e sem nomes que começam com `_`, em ordem alfabética sem diferenciar maiúsculas. Reaproveita o `ScanResult` quando o `mtime` não mudou;
        *   `get(name, rescan_if_changed=True) -> ScriptEntry`;
        *   `add_script(src_path, overwrite: bool) -> ScriptEntry`: copia com `shutil.copy2`. Se o destino existir e `overwrite=False`, lança `FileExistsError` para a interface perguntar;
    *   `params_signature(scan) -> tuple`: assinatura dos parâmetros (nome, tipo, opções, obrigatório). O app compara essa assinatura logo antes de executar para detectar mudança.

#### 8. `runpython/core/validation.py` (Criar)

*   **Tipo / Escopo:** conversão e validação, sem Tk.
*   **Mudanças:**
    *   `parse_value(spec, raw: str | bool) -> (valor, erro | None)`:
        *   `int` usa `int()` sobre o texto limpo;
        *   `float` troca `,` por `.`;
        *   `bool` passa direto;
        *   `file` e `folder` aplicam `os.path.expandvars` e `strip()`;
    *   `validate(spec, valor) -> erro | None`: obrigatório, `min`/`max`, `options` e existência conforme `must_exist`/`save` (para `save`, confere se a pasta-pai existe);
    *   `validate_all(specs, raw_values) -> (values, errors: dict[nome, msg])`;
    *   todas as mensagens em português, por exemplo "Informe um número inteiro" e "A pasta não existe".

#### 9. `runpython/core/values_store.py` (Criar)

*   **Tipo / Escopo:** últimos valores por script.
*   **Mudanças:**
    *   `load(script_name) -> StoredValues(values, orphans)`;
    *   `save(script_name, values, orphans)`: atômico, em `values/<script_name>.json`;
    *   `merge(specs, stored) -> (form_values, orphans, notices: list[str])`: aplica a tabela da seção 4 do Plano técnico, ou seja, nome atual, depois `aliases`, conversão de tipo via `validation.parse_value`, opção que sumiu e valores órfãos;
    *   um arquivo corrompido é renomeado para `.bak`, com um aviso, e o script começa vazio.

#### 10. `runpython/core/helper_install.py` (Criar)

*   **Tipo / Escopo:** cópia do `psr.py` para a pasta de scripts.
*   **Mudanças:**
    *   `read_version(path) -> str | None`: regex `^PSR_VERSION\s*=\s*"(.+)"` sobre o texto, sem importar o arquivo;
    *   `ensure_helper(scripts_dir) -> HelperResult(action: "ok" | "installed" | "updated", version)`: compara a versão do `psr.py` da pasta com a do `bundled_psr_path()`. Se forem diferentes, ou se o arquivo não existir, copia com `atomic_write_text`. Erros de permissão viram `HelperInstallError`, com mensagem em português.

#### 11. `runpython/core/python_env.py` (Criar)

*   **Tipo / Escopo:** qual Python executa os scripts.
*   **Mudanças:**
    *   `default_python() -> str`: se `sys.executable` termina em `pythonw.exe`, devolve o `python.exe` da mesma pasta; senão, devolve o próprio `sys.executable`;
    *   `resolve(cfg) -> str`: usa `cfg.python_path`, ou o padrão;
    *   `check(python_path) -> (ok, versão | erro)`: roda `[python, "-c", "import sys;print(sys.version)"]` com tempo-limite de 10 s e `CREATE_NO_WINDOW`.

#### 12. `runpython/core/winjob.py` (Criar)

*   **Tipo / Escopo:** Job Object do Windows via `ctypes`.
*   **Mudanças:**
    *   `class Job`:
        *   `__init__()`: `CreateJobObjectW` e `SetInformationJobObject` com `JOBOBJECT_EXTENDED_LIMIT_INFORMATION.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`;
        *   `assign(pid)`: `OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE)` e `AssignProcessToJobObject`;
        *   `terminate(exit_code=1)`: `TerminateJobObject`;
        *   `close()`: `CloseHandle`;
    *   se qualquer chamada falhar, o erro é registrado e `terminate()` passa a usar `taskkill /T /F /PID` como alternativa.

#### 13. `runpython/core/runner.py` (Criar)

*   **Tipo / Escopo:** executa um script e transmite a saída.
*   **Mudanças:**
    *   `RunState` (enum): `IDLE`, `RUNNING`, `SUCCESS`, `FAILED`, `ABORTED`, `NOT_STARTED`;
    *   `LogLine(stream: "out" | "err" | "sys", text)`;
    *   `class Runner`, com `start(...)`, `abort()` e `poll()`:
        *   **`start(script_path, scripts_dir, python, values, on_finish)`:**
            1.  `helper_install.ensure_helper`;
            2.  grava o JSON em `tempfile.mkstemp(prefix="psr_", suffix=".json")`;
            3.  monta o ambiente: `PSR_PARAMS_FILE`, `PYTHONIOENCODING=utf-8`, e `PYTHONPATH` com a pasta dos scripts antes do valor atual;
            4.  executa o `Popen` da seção 6 do Plano técnico;
            5.  `Job().assign(pid)`;
            6.  inicia duas threads, que leem linha a linha (`errors="replace"`) e colocam `LogLine` numa `queue.Queue`;
            7.  inicia uma terceira thread que espera `proc.wait()`, espera as duas leitoras terminarem, calcula o estado, apaga o JSON (`finally`), fecha o job e coloca o evento de fim na fila;
        *   **`abort()`:** marca `aborted=True` e chama `job.terminate()`;
        *   **`poll() -> list[evento]`:** esvazia a fila sem bloquear. A interface chama a cada 50 ms;
        *   qualquer exceção antes do `Popen` resulta em `NOT_STARTED`, com a mensagem;
    *   `RunResult`: `state`, `exit_code`, `duration_s` e `log_path`.

#### 14. `runpython/core/error_hints.py` (Criar)

*   **Tipo / Escopo:** traduz erros comuns.
*   **Mudanças:**
    *   `MODULE_TO_PACKAGE`: a tabela da seção 6 do Plano técnico;
    *   `find_hint(stderr_lines, python) -> Hint | None`: procura `ModuleNotFoundError: No module named '(\w+)` (só o primeiro trecho antes do `.`) e devolve `Hint(title="Falta o pacote X", command='"<python>" -m pip install <pacote>')`;
    *   também reconhece `FileNotFoundError` e `PermissionError`, com uma frase curta em português.

#### 15. `runpython/core/run_log.py` (Criar)

*   **Tipo / Escopo:** arquivo de log por execução.
*   **Mudanças:**
    *   `RunLogWriter(script_name)`:
        *   `open(header: dict)` grava um cabeçalho com Python, versão do `psr.py`, valores e horário;
        *   `write(LogLine)` grava com o prefixo `[err]` nas linhas de stderr;
        *   `close(result)` grava o estado, o código de saída e a duração;
    *   `prune(script_name, keep=20)` apaga os logs mais antigos;
    *   `last_result(script_name) -> (estado, datetime) | None`: lê o rodapé do log mais recente, para o status na barra lateral.

#### 16. `runpython/ui/theme.py` (Criar)

*   **Tipo / Escopo:** aparência.
*   **Mudanças:**
    *   `enable_dpi_awareness()`: tenta `SetProcessDpiAwareness(2)`; se falhar, usa `SetProcessDPIAware()`;
    *   `apply(root, theme)`: importa `runpython.vendor.sv_ttk` e chama `set_theme("light"/"dark")`. Para "system", lê `AppsUseLightTheme` em `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`;
    *   define as fontes (`Segoe UI` 10, título 14 em negrito) e as cores do log (stderr em vermelho, mensagens do sistema em cinza).

#### 17. `runpython/ui/app.py` (Criar)

*   **Tipo / Escopo:** janela principal e coordenação.
*   **Mudanças:**
    *   `main()`: chama `applog.setup()`, `config.load()`, cria o `Tk` e chama `theme.apply`;
        *   se `scripts_dir` for nulo, pede a pasta (`askdirectory`, sugerindo `Documentos\RunPython\scripts`, criada se o usuário aceitar);
        *   instala o `report_callback_exception`, que registra o erro e mostra uma caixa de diálogo;
    *   `class MainWindow`: um `ttk.Panedwindow` horizontal, com `Sidebar` à esquerda e a área principal à direita. A área principal é um `Panedwindow` vertical, com `ScriptView` (formulário + `RunBar`) em cima e `LogPanel` embaixo.
        *   **`on_select(name)`:** `library.get`;
            *   se o scan tiver erro, mostra o painel de erros (lista de linha e mensagem);
            *   senão, faz `values_store.merge` e `form.build(specs, values)`, e mostra as notas de merge numa faixa informativa;
        *   **`on_run()`:**
            1.  relê o script e compara `params_signature`. Se mudou, reconstrói o formulário, mostra "O script mudou, confira os campos" e para;
            2.  `validation.validate_all`. Se houver erro, mostra nos campos e para;
            3.  `values_store.save`;
            4.  `runner.start`;
            5.  troca o botão Executar por Abortar e marca a barra lateral com "Executando…";
        *   **`_pump()`:** a cada 50 ms, chama `runner.poll()` e repassa as linhas para `LogPanel.append_batch` e `RunLogWriter`. No evento de fim, atualiza `RunBar`, `Sidebar` e `error_hints`;
        *   **`on_close()`:** se estiver em execução, pergunta "Abortar e sair?". Depois salva a geometria e o último script e fecha.

#### 18. `runpython/ui/sidebar.py` (Criar)

*   **Tipo / Escopo:** barra lateral.
*   **Mudanças:**
    *   título;
    *   botão "+ Adicionar script": `askopenfilename` com filtro `*.py`, depois `library.add_script`. Em `FileExistsError`, pergunta antes de sobrescrever;
    *   campo de busca, que filtra ao digitar;
    *   `ttk.Treeview` de uma coluna, com o nome em negrito e a linha de status, e um ícone de texto conforme o estado (●, ✓, ✗, ⚠);
    *   rodapé com Abrir pasta (`os.startfile`), Recarregar e Configurações;
    *   `set_status(name, texto)`, `set_running(name, bool)` e `select(name)`.

#### 19. `runpython/ui/form.py` (Criar)

*   **Tipo / Escopo:** monta o formulário a partir dos `ParamSpec`.
*   **Mudanças:**
    *   `ScrollableFrame`: um `Canvas` com `Frame` interno, barra de rolagem e roda do mouse;
    *   `ScriptView`:
        *   cabeçalho com nome, caminho, descrição e botão Restaurar padrões;
        *   `build(specs, values)` agrupa os parâmetros por `group`, na ordem de primeira aparição (sem grupo vai para "Geral"), e cria um `ttk.Labelframe` por grupo;
        *   para cada spec, chama `fields.create(parent, spec, value)`;
        *   grade de 2 colunas quando a largura passa de 900 px (por `<Configure>`), 1 coluna abaixo disso; campos `bool` ocupam a linha inteira;
        *   `get_raw_values()`, `show_errors(dict)`, `reset_defaults()` e `set_enabled(bool)` (desativa tudo durante a execução);
        *   validação ao sair de cada campo (`<FocusOut>`), que habilita ou desabilita o botão Executar;
        *   `show_scan_errors(issues)`: mostra os erros de marcador no lugar do formulário.

#### 20. `runpython/ui/fields.py` (Criar)

*   **Tipo / Escopo:** um widget por tipo.
*   **Mudanças:**
    *   `create(parent, spec, value) -> Field`, com `get()`, `set(v)`, `set_error(msg)` e `widget`;
    *   rótulo com `*` quando obrigatório e a ajuda em cinza embaixo;
    *   tipos: `TextField`, `NumberField` (int/float), `BoolField` (Checkbutton), `ChoiceField` (Combobox `state="readonly"`), `FileField` (Entry + "Procurar…", usando `filetypes` e `save`) e `FolderField`.

#### 21. `runpython/ui/runbar.py` (Criar)

*   **Tipo / Escopo:** barra de execução.
*   **Mudanças:**
    *   faixa escura com o texto de estado, por exemplo "Pronto para executar", "Executando… 00:42", "Sucesso em 12 s" ou "Falhou (código 1)";
    *   botão Executar/Abortar;
    *   cronômetro atualizado a cada segundo;
    *   faixa de dica (`Hint`) com o comando e o botão **Copiar**.

#### 22. `runpython/ui/log_panel.py` (Criar)

*   **Tipo / Escopo:** log ao vivo.
*   **Mudanças:**
    *   `tk.Text` somente leitura, fonte `Consolas` 10, com as tags `err` e `sys`;
    *   `append_batch(lines)`: insere tudo de uma vez, apaga do topo se passar de 10.000 linhas e rola para o fim só se o usuário já estava no fim;
    *   botões Copiar log, Salvar log (`asksaveasfilename`), Abrir pasta do script, Copiar diagnóstico e Limpar;
    *   começa recolhido e abre na primeira execução.

#### 23. `runpython/ui/settings_dialog.py` (Criar)

*   **Tipo / Escopo:** janela de Configurações (`Toplevel` modal).
*   **Mudanças:**
    *   pasta de scripts (Procurar…);
    *   Python (Procurar… `python.exe`, mais o botão Testar, que usa `python_env.check`);
    *   tema (Sistema/Claro/Escuro);
    *   botões Salvar e Cancelar;
    *   se a pasta mudar, chama `library` refresh.

#### 24. `runpython/vendor/sv_ttk/` (Criar)

*   **Tipo / Escopo:** dependência embutida.
*   **Mudanças:** cópia do pacote sv-ttk (versão 2.6.x): `__init__.py`, `sv.tcl` e a pasta `theme/`, junto com o `LICENSE` (MIT).
*   **Por quê:** o app não pode exigir `pip install`.

#### 25. `docs/MARKER_SPEC.md` (Criar)

*   **Tipo / Escopo:** documentação para quem escreve ou converte scripts.
*   **Mudanças:**
    *   formato `psr-format: 1`;
    *   tabela de tipos e argumentos;
    *   regras (nível do módulo, só literais);
    *   exemplos por tipo;
    *   erros comuns e a mensagem que o app mostra;
    *   **passo a passo de conversão:**
        1.  localizar as variáveis fixas;
        2.  mover para o topo;
        3.  trocar `X = valor` por `X = param("tipo", default=valor, label=...)`;
        4.  acrescentar `from psr import param` e a docstring;
        5.  abrir no app e conferir;
    *   como rodar pela linha de comando (usa os padrões);
    *   limitações: sem subpastas, valores perdidos ao renomear o script, `input()` não funciona.

#### 26. `examples/exemplo_relatorio.py` (Criar)

*   **Tipo / Escopo:** script de exemplo que usa todos os 7 tipos e 2 grupos, imprime os valores recebidos e simula trabalho com `time.sleep`.
*   **Por quê:** serve de modelo para a conversão e de teste manual do app.

#### 27. `README.md` (Criar)

*   **Tipo / Escopo:** documentação do projeto.
*   **Mudanças:**
    *   requisitos (Python 3.9+ com Tkinter);
    *   como abrir (duplo clique em `RunPython.pyw`);
    *   onde ficam os dados (`%APPDATA%\RunPython`);
    *   link para `docs/MARKER_SPEC.md`;
    *   como rodar os testes.

#### 28. `pyproject.toml` (Criar)

*   **Tipo / Escopo:** configuração do projeto.
*   **Mudanças:**
    *   `requires-python = ">=3.9"`;
    *   **sem dependências de execução**;
    *   dependências de desenvolvimento opcionais: `pytest` e `ruff`;
    *   configuração do ruff (`target-version = "py39"`, excluindo `runpython/vendor`) e do pytest (`testpaths = ["tests"]`).

#### 29. `.gitignore` (Criar)

*   **Mudanças:** `__pycache__/`, `.pytest_cache/`, `.ruff_cache/` e `*.pyc`.

#### 30. Testes (Criar)

*   **`tests/conftest.py`:** fixtures:
    *   `tmp_scripts_dir`;
    *   `appdata_tmp`, que redireciona `%APPDATA%` para uma pasta temporária via `monkeypatch`;
    *   `bundled_psr`.
*   **`tests/fixtures/markers/`:** pares `nome.py` + `nome.expected.json`, cobrindo:
    *   todos os tipos;
    *   chamada em várias linhas;
    *   docstring;
    *   `psr-format` ausente, 1 e 2;
    *   argumento não literal;
    *   `param()` dentro de `if` ou de função;
    *   tipo desconhecido;
    *   chave desconhecida (aviso);
    *   nome repetido;
    *   `choice` sem opções;
    *   erro de sintaxe;
    *   arquivo em cp1252 com declaração `coding`;
    *   arquivo com BOM.
*   **`tests/test_psr_scan.py`:** para cada fixture, `scan_file` precisa produzir o `.expected.json` (parâmetros e issues).
*   **`tests/test_psr_runtime.py`:** roda scripts de teste num subprocesso:
    *   sem `PSR_PARAMS_FILE`, recebe os padrões;
    *   com o JSON, recebe os valores;
    *   uma chamada em várias linhas recebe o valor certo;
    *   um processo filho de `multiprocessing` recebe os mesmos valores.
*   **`tests/test_no_execution.py`:** `scan_file` sobre um script que cria um arquivo, abre uma conexão e chama `sys.exit` no topo. Confere que nada aconteceu.
*   **`tests/test_validation.py`:** int, float com vírgula, `min`/`max`, `required`, `must_exist`, `save` e `choice`.
*   **`tests/test_values_store.py`:** cada linha da tabela de merge (novo, renomeado via `aliases`, removido para órfão, tipo mudou, opção sumiu) e um arquivo corrompido indo para `.bak`.
*   **`tests/test_helper_install.py`:** cópia quando falta, atualização quando a versão é diferente, nada quando é igual e erro em pasta só de leitura.
*   **`tests/test_scanner.py`:** ignora `psr.py`, `_x.py` e subpastas; reaproveita o scan pelo `mtime`; `add_script` com e sem sobrescrever.
*   **`tests/test_runner.py`:**
    *   sucesso (código 0);
    *   falha (código 2);
    *   saída com acentos chega sem corromper;
    *   10.000 linhas chegam completas;
    *   o JSON temporário é apagado nos três finais;
    *   `NOT_STARTED` com Python inválido;
    *   `input()` recebe EOF e não trava.
*   **`tests/test_winjob.py`:** o script abre 2 filhos com `multiprocessing` que dormem 60 s. Depois de `abort()`, nenhum dos 3 PIDs existe (conferido com `OpenProcess` ou `tasklist`). Só roda no Windows.
*   **`tests/test_error_hints.py`:** `cv2` vira `opencv-python`; um módulo desconhecido vira o próprio nome; nenhuma dica quando não há erro.

### Plano de verificação

*   **Build:** não há build. O app roda direto com `pythonw RunPython.pyw`.
*   **Testes unitários e de integração:** `python -m pytest`, que precisa passar no Python 3.9 e no 3.12 do python.org.
*   **Análise estática:** `ruff check runpython tests` sem erros.
*   **Cobertura:** 85% ou mais das linhas em `runpython/psr.py` e `runpython/core/` (`pytest --cov`). A interface é verificada manualmente.
*   **Roteiro manual (em ordem):**
    1.  **Primeira abertura:** pede a pasta e cria `Documentos\RunPython\scripts`.
    2.  **CUJ 1:** adicionar `examples/exemplo_relatorio.py` pelo botão, preencher e executar. Conferir: log ao vivo, "Sucesso", `psr.py` copiado e valores lembrados ao reabrir.
    3.  **CUJ 2:** editar o exemplo, acrescentando um parâmetro obrigatório e renomeando outro com `aliases`, e clicar em Recarregar.
    4.  **CUJ 3:** script com `import pandas` num Python sem pandas: aparece a dica com o comando.
    5.  **CUJ 4:** script com `multiprocessing`, Abortar, e conferir no Gerenciador de Tarefas que não sobrou nenhum `python.exe`.
    6.  **CUJ 5:** script com `default=abc`: aparece o selo de erro com a linha.
    7.  **Mudança antes de executar:** editar o script com o formulário aberto e clicar em Executar. Aparece o aviso, e o script não roda.
    8.  **Tela:** escala do Windows em 150%, tema escuro e janela estreita (1 coluna).
    9.  **Linha de comando:** `python exemplo_relatorio.py` na pasta de scripts roda com os padrões.
    10. **Python da Microsoft Store:** repetir os passos 2 e 5.

--------------------------------------------------------------------------------

*Drafted with EGM*
