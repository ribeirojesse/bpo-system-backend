#!/bin/bash
# Backup do RDS (pg_dump) + dos uploads (OFX/holerites/faturas) pro S3.
#
# Roda NA EC2. Usa a role IAM da instância pra falar com o S3 — não
# precisa (e não deve) ter access key/secret key salvos aqui.
#
# Uso manual:   bash ~/app/deploy/aws/scripts/backup_to_s3.sh
# Uso agendado: crontab -e (o caminho completo é obrigatório):
#   0 3 * * * /bin/bash /home/ec2-user/app/deploy/aws/scripts/backup_to_s3.sh >> /home/ec2-user/backup.log 2>&1
#
# DATABASE_URL e S3_BUCKET vêm do .env da aplicação ($APP_DIR/.env) —
# nada de credencial escrita aqui dentro. Se faltar qualquer um dos
# dois, o script para com erro em vez de gerar um backup vazio.

set -euo pipefail

APP_DIR="/home/ec2-user/app"

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "[$TIMESTAMP] ERRO: $APP_DIR/.env não existe." >&2
  exit 1
fi

# Lê uma variável do .env sem exportar o arquivo inteiro (e sem quebrar
# em valores que tenham "=" no meio, como a senha do banco).
ler_env() {
  # tr -d '\r': .env editado no Windows deixa CR no fim da linha, que
  # entraria dentro do valor e quebraria a conexão de um jeito difícil
  # de enxergar.
  grep -E "^$1=" .env \
    | head -1 \
    | cut -d= -f2- \
    | tr -d '"\r' \
    | sed -e "s/^'//" -e "s/'$//"
}

# O .env guarda a URL no formato do SQLAlchemy ("postgresql+psycopg2://"),
# que o pg_dump não reconhece — sem trocar o prefixo ele acha que a
# string é um nome de banco e tenta o socket local.
DATABASE_URL=$(
  ler_env DATABASE_URL | sed 's#^postgresql+[a-z0-9]*://#postgresql://#'
)
S3_BUCKET=$(ler_env S3_BUCKET || true)

# A versão anterior montava o comando com a variável vazia e o pg_dump
# tentava o socket local ("connection to server on socket ... failed"),
# que é um jeito confuso de dizer "faltou a URL do banco".
if [ -z "$DATABASE_URL" ]; then
  echo "[$TIMESTAMP] ERRO: DATABASE_URL não encontrado em $APP_DIR/.env" >&2
  exit 1
fi

if [ -z "$S3_BUCKET" ]; then
  echo "[$TIMESTAMP] ERRO: S3_BUCKET não encontrado em $APP_DIR/.env" >&2
  echo "   Acrescente no .env: S3_BUCKET=bpo-system-backups-SEU-ID" >&2
  exit 1
fi

echo "[$TIMESTAMP] Gerando dump do Postgres..."
# Container temporário com o cliente do Postgres (a imagem da API não
# tem pg_dump — só a lib psycopg2 pra falar com o banco).
docker run --rm postgres:16-alpine \
  pg_dump "$DATABASE_URL" | gzip > "$TMP_DIR/db_${TIMESTAMP}.sql.gz"

# Dump vazio = backup inútil. Melhor falhar aqui do que descobrir na
# hora de restaurar.
TAMANHO=$(stat -c%s "$TMP_DIR/db_${TIMESTAMP}.sql.gz")

if [ "$TAMANHO" -lt 1024 ]; then
  echo "[$TIMESTAMP] ERRO: dump saiu com $TAMANHO bytes — abortando." >&2
  exit 1
fi

echo "[$TIMESTAMP] Compactando uploads..."
docker run --rm \
  -v bpo-system_uploads_data:/uploads:ro \
  -v "$TMP_DIR":/backup \
  alpine sh -c "tar -czf /backup/uploads_${TIMESTAMP}.tar.gz -C /uploads ."

echo "[$TIMESTAMP] Enviando pro S3..."
aws s3 cp "$TMP_DIR/db_${TIMESTAMP}.sql.gz" "s3://${S3_BUCKET}/db/db_${TIMESTAMP}.sql.gz"
aws s3 cp "$TMP_DIR/uploads_${TIMESTAMP}.tar.gz" "s3://${S3_BUCKET}/uploads/uploads_${TIMESTAMP}.tar.gz"

echo "[$TIMESTAMP] Backup concluído: db_${TIMESTAMP}.sql.gz ($(( TAMANHO / 1024 )) KB) e uploads_${TIMESTAMP}.tar.gz"
