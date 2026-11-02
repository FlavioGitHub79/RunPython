"""Exemplo do RunPython: lê os arquivos de uma pasta e gera um resumo.

Use este script como modelo para converter os seus. Ele usa todos os tipos de parâmetro.
"""
# psr-format: 1
import os
import time

from psr import param

PASTA = param("folder", default=r"C:\Windows\Web", label="Pasta de entrada",
              help="Pasta cujos arquivos serão listados.", group="Arquivos", required=True)
SAIDA = param("file", default="", label="Salvar resumo em",
              filetypes=[("Texto", "*.txt")], save=True, group="Arquivos",
              help="Opcional. Deixe vazio para só mostrar no log.")
EXTENSAO = param("choice", default="todas", options=["todas", ".jpg", ".png", ".txt"],
                 label="Tipo de arquivo", group="Arquivos")
LIMITE = param("int", default=50, min=1, max=10000, label="Máximo de arquivos", group="Execução")
PAUSA = param("float", default=0.05, min=0, max=2, label="Pausa entre arquivos (s)",
              help="Só para ver o log ao vivo funcionando.", group="Execução")
TITULO = param("text", default="Resumo", label="Título do relatório", group="Execução")
DETALHADO = param("bool", default=True, label="Mostrar o tamanho de cada arquivo", group="Execução")


def main() -> None:
    print(f"== {TITULO} ==")
    print(f"Pasta: {PASTA}")
    linhas = []
    total = 0
    for raiz, _dirs, arquivos in os.walk(PASTA):
        for nome in arquivos:
            if EXTENSAO != "todas" and not nome.lower().endswith(EXTENSAO):
                continue
            caminho = os.path.join(raiz, nome)
            tamanho = os.path.getsize(caminho)
            total += 1
            linha = f"{nome} ({tamanho:,} bytes)" if DETALHADO else nome
            linhas.append(linha)
            print(linha)
            time.sleep(PAUSA)
            if total >= LIMITE:
                break
        if total >= LIMITE:
            break
    print(f"Total: {total} arquivo(s)")
    if SAIDA:
        with open(SAIDA, "w", encoding="utf-8") as f:
            f.write(f"{TITULO}\n\n" + "\n".join(linhas) + f"\n\nTotal: {total}\n")
        print(f"Resumo salvo em {SAIDA}")


if __name__ == "__main__":
    main()
