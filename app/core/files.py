import os
import time
import uuid


def gerar_nome_seguro(filename: str) -> str:
    """Gera um nome de arquivo seguro para salvar em disco.

    Nunca usa o nome enviado pelo cliente diretamente no caminho de
    gravação (evita path traversal, ex: "../../app/main.py") e evita
    colisão entre uploads diferentes com o mesmo nome de arquivo.

    Mantém apenas a extensão original (também sanitizada).
    """

    nome_original = os.path.basename(filename or "")

    _, extensao = os.path.splitext(nome_original)

    extensao = "".join(
        c for c in extensao
        if c.isalnum() or c == "."
    )[:10]

    return f"{uuid.uuid4().hex}{extensao}"


def limpar_uploads_antigos(
    diretorio: str,
    dias: int = 30
) -> int:
    """Remove arquivos de `diretorio` com mais de `dias` dias.

    Não é chamada automaticamente em nenhum lugar (não há
    agendador/cron neste projeto) — é uma utilidade que pode ser
    invocada manualmente ou ligada a um job/cron futuro. Retorna a
    quantidade de arquivos removidos.
    """

    if not os.path.isdir(diretorio):
        return 0

    limite = time.time() - (dias * 86400)

    removidos = 0

    for nome in os.listdir(diretorio):

        caminho = os.path.join(diretorio, nome)

        if not os.path.isfile(caminho):
            continue

        if os.path.getmtime(caminho) < limite:

            try:
                os.remove(caminho)
                removidos += 1
            except OSError:
                continue

    return removidos
