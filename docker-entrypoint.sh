#!/bin/sh
set -e

# --reload é uma flag de desenvolvimento (fica observando mudanças de
# arquivo em disco); em produção só adiciona overhead e é indesejado.
if [ "$ENVIRONMENT" = "production" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
