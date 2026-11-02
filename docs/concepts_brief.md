# Python Script Runner (RunPython)

* **Autor:** flavio.lp@gmail.com
* **Data:** 2026-11-02

## Visão geral

App desktop para Windows, local e leve, que lê uma pasta de scripts Python e lista esses scripts numa barra lateral. Ao selecionar um script, o app lê o código **sem executá-lo**, encontra os parâmetros marcados e monta um formulário com um campo para cada um. Os campos ficam organizados em grupos, como no design do Stitch. O usuário preenche, clica em **Iniciar execução** e acompanha o **log ao vivo**. Ele pode **abortar** a execução a qualquer momento.

Os scripts rodam no Python já instalado na máquina, num ambiente único compartilhado. Cada pessoa usa o app só na própria máquina. Quem usa pode não ser técnico.

Os scripts atuais têm valores fixos no código (hardcoded) e serão convertidos manualmente para o formato de marcadores. A `skill.md` para o assistente de IA foi retirada do escopo.

## Análise (revisão com 6 lentes)

### 1. Como o valor chega ao script (bloqueante)
O conceito original não definia isso. As opções simples falham:
- Injetar valores antes de rodar não funciona, porque a linha `PASTA = ...` do script sobrescreve o valor.
- Reescrever o arquivo antes de rodar quebra `multiprocessing` no Windows.
- Passar pela linha de comando tem problemas de aspas e limite de tamanho, e expõe senhas.

**Contrato proposto:**
1. O app grava os valores num JSON temporário.
2. O app passa o caminho desse JSON numa variável de ambiente (`PSR_PARAMS_FILE`).
3. Um helper pequeno, só com a biblioteca padrão, lê esse JSON dentro do script.
4. O app apaga o JSON no fim da execução.

Processos filhos herdam a variável de ambiente, então `multiprocessing` continua funcionando. Sem o app, o script usa os valores padrão e roda normalmente pela linha de comando.

### 2. Formato do marcador (bloqueante)
Recomendação: uma chamada `param()` só com valores literais.

```python
from psr import param

PASTA  = param("folder", default=r"C:\dados", label="Pasta de entrada", group="Arquivos", required=True)
LIMITE = param("int", default=10, label="Limite de linhas", group="Execução")
FORMATO = param("choice", default="csv", options=["csv", "parquet"], label="Formato de saída")
```

- O app lê esses parâmetros com o módulo `ast` do Python e `literal_eval`. Isso só lê o texto, **não executa** nada do script.
- A conversão dos scripts atuais é 1 para 1: cada variável fixa vira um `param(...)`.
- Precisa de uma **especificação única e versionada** (`MARKER_SPEC`), com:
  - lista fechada de tipos;
  - scripts de exemplo com o resultado esperado da leitura;
  - um cabeçalho `# psr-format: 1` em cada script.

  O leitor do app usa esses exemplos nos testes. A especificação também serve de manual para quem converte ou escreve scripts. Sem a skill, o app mostra o erro do marcador ao lado do script, porque o selo de erro é a única verificação.

### 3. Execução no Windows
- **Abortar** precisa matar a árvore inteira de processos (Job Object). `terminate()` deixa processos filhos vivos.
- Rodar com:
  - `stdin` fechado, para `input()` não travar a execução;
  - sem janela de console;
  - saída sem buffer (`-u`);
  - `PYTHONIOENCODING=utf-8`, para acentos aparecerem certos no log.
- Ler a saída numa thread separada e atualizar a tela em lotes. Senão, um script que imprime muito trava a interface.
- Localizar o Python nesta ordem: `py -0p`, registro do Windows, PATH. Descartar o `python.exe` falso da Microsoft Store, que só abre a loja.

### 4. Presets e scripts que mudam
Quando o script muda, o app relê os parâmetros e ajusta a tela. Os valores salvos precisam de regras:

| Situação | Comportamento |
| :-- | :-- |
| Parâmetro novo | Aparece na tela. Se for obrigatório, o botão Executar fica bloqueado até ser preenchido. |
| Parâmetro renomeado | Mapeado via `aliases=[...]` no `param()`. |
| Parâmetro removido | O valor fica guardado como "órfão", com aviso. |
| Tipo mudou | O app tenta converter. Se não der, descarta o valor e avisa. |
| Opção do dropdown sumiu | Volta para o valor padrão. |

Dados salvos em `%APPDATA%`, com versão, em gravação atômica.

### 5. Experiência para quem não é técnico
- O erro mais comum será **pacote faltando**. Mostrar "Falta o pacote X" com o comando `pip install` pronto para copiar. Atenção a nomes diferentes, como `cv2`, que se instala com `opencv-python`.
- A execução termina em 4 estados claros: **sucesso**, **falhou**, **parado por você**, **não iniciou**. O log bruto fica recolhido.
- Erro de validação aparece ao lado do campo. Números aceitam vírgula decimal ("3,5").
- O app pede confirmação para fechar durante uma execução. Botões "Abrir pasta", "Copiar log" e "Salvar log".
- Script com marcador quebrado continua na lista com um selo de erro. O app não pode fechar sozinho por causa disso.
- Interface em um idioma só (português). O design atual mistura português e inglês.

### 6. Segurança e diagnóstico
- O app descobre os parâmetros só lendo o código, nunca importando o script. Um teste garante isso: um script que criaria um arquivo se fosse executado.
- Execução com lista de argumentos, nunca `shell=True`.
- Senhas não vão para presets, logs nem para o JSON depois da execução.
- Um log por execução com Python usado, valores, código de saída e duração. O app guarda os últimos N. Botão "Copiar diagnóstico".

### 7. Tecnologia da interface
Recomendação: **Python + Tkinter/ttk com o tema sv-ttk**, rodando como `.pyw` no Python do próprio usuário.
- Não precisa instalar nada a mais.
- O leitor de marcadores e os scripts usam o mesmo Python.
- É leve. Com o tema, o visual fica moderno e a interface fluida, desde que o log seja atualizado em lotes.
- Precisa de suporte a DPI alto e de uma checagem de que o Tk existe no Python instalado.

Alternativa, se o visual do Stitch for obrigatório: **Tauri (WebView2)**, reaproveitando o mesmo leitor e helper em Python.

## Objetivos e não-objetivos

**Dentro do escopo (v1):**
- Barra lateral com os scripts da pasta, busca e status.
- Leitura dos parâmetros sem executar o script.
- Tipos: texto, inteiro, decimal, sim/não, lista de opções, arquivo (com filtro de extensão), pasta.
- Rótulo, ajuda, obrigatório, valor padrão e grupos.
- Executar, Restaurar padrões e Abortar.
- Log ao vivo e estado final claro.
- Últimos valores lembrados automaticamente.
- Ajuste da tela quando o script muda.
- Documento `MARKER_SPEC` com tipos, exemplos e um passo a passo para converter scripts hardcoded.

**A decidir:** presets com nome, tipos data e senha, monitoramento automático da pasta, vários scripts rodando ao mesmo tempo, `.exe` empacotado.

**Fora do escopo:** `skill.md` para o assistente de IA, agendamento, terminal global, webhooks e notificações, perfil e login, rede ou execução compartilhada, um venv por script.

## Alternativas avaliadas

| Alternativa | Por que foi rejeitada |
| :-- | :-- |
| Marcador em comentário (`# @param ...`) | O `ast` descarta comentários. Exigiria um segundo leitor e uma mini-linguagem com regras de aspas, e ainda um jeito de injetar os valores. Segunda melhor opção. |
| `argparse` | Ler as definições sem executar é frágil. Um modo "exportar schema" executaria código do script. |
| Bloco YAML/JSON no topo | YAML não vem com o Python. A definição fica longe da variável que controla. |
| Gooey | Sem manutenção desde cerca de 2021. Depende do wxPython. Uma janela por script, sem app central. |
| Streamlit / NiceGUI | Sobem um servidor local e abrem o navegador. Execuções longas e o botão Abortar ficam difíceis. |
| PySide6 / Qt | Entre 60 e 200 MB, mais pesado que o necessário. |
| C# WPF | Segunda linguagem para manter. Não reaproveita o leitor em Python. |
| Electron | Pesado demais. |

## Decisões e próximos passos

**Decidido:**
- App local, um Python compartilhado, pasta local.
- Log ao vivo.
- Fora do escopo: agendamento, terminal, webhook e login.
- Os scripts atuais serão convertidos.

- A `skill.md` foi retirada do escopo.
- Marcador `param()`, com `from psr import param` dentro dos scripts.
- Contrato JSON + variável de ambiente + helper.
- Tkinter + sv-ttk (visual nativo moderno, não idêntico ao Stitch).
- Especificação de marcadores versionada (`MARKER_SPEC`).
- Execução sem `input()` (stdin fechado).
- Abortar mata a árvore inteira de processos.
- Erro de pacote faltando com o `pip install` pronto.
- Regras de presets da tabela da seção 4.

**Padrões adotados na v1 (a menos que você diga o contrário):**
- Um script rodando por vez.
- Só os últimos valores usados. Presets com nome ficam para depois.
- Sem os tipos data e senha.
- Uma pasta de scripts, escolhida nas configurações.
- O app não instala pacotes sozinho; só mostra o comando.

**A verificar durante a implementação:**
1. Algum script atual usa `input()` ou caminhos relativos à pasta do script? Proposta: o app roda o script com a pasta de trabalho igual à pasta do script.
2. Como o Python foi instalado nas máquinas (python.org, Microsoft Store, conda)? O Tkinter está incluído? O app checa isso ao abrir.
