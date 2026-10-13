#!/bin/sh
set -e

# --reload é uma flag de desenvolvimento (fica observando mudanças de
# arquivo em disco); em produção só adiciona overhead e é indesejado.
#
# --proxy-headers --forwarded-allow-ips="*": em produção o Uvicorn só
# recebe conexões do nginx (a API não é exposta direto pra internet —
# ver docker-compose.prod.yml, "expose" em vez de "ports"), então
# confiar em qualquer IP aqui é seguro. Sem isso, o Uvicorn ignora o
# X-Forwarded-Proto que o nginx já manda, acha que toda conexão é HTTP
# (já que internamente nginx -> api realmente é HTTP sem TLS) e monta
# qualquer redirect automático (ex: FastAPI adicionando a barra final
# em "/admin/users" -> "/admin/users/") como "http://..." — o que o
# navegador bloqueia como mixed content numa página servida por https.
#
# WEB_CONCURRENCY = número de processos (workers) da API. Padrão 1: o rate
# limit (app/core/rate_limit.py) conta na memória de cada processo, então
# com N workers os limites de login/IA ficam até N vezes mais frouxos (o
# limit_req do nginx continua global). Após subir a EC2 para t3.small,
# defina WEB_CONCURRENCY=2 no .env e recrie o container.
if [ "$ENVIRONMENT" = "production" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        --workers "${WEB_CONCURRENCY:-1}" \
        --proxy-headers --forwarded-allow-ips="*"
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
