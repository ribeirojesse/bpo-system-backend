#!/bin/bash
# Backup do RDS (pg_dump) + dos uploads (OFX/holerites) pro S3.
#
# Roda NA EC2. Usa a role IAM da instância pra falar com o S3 — não
# precisa (e não deve) ter access key/secret key salvos aqui.
#
# Uso manual:   ./backup_to_s3.sh
# Uso agendado: crontab (ver DEPLOY.md) — ex. todo dia às 3h da manhã.

set -euo pipefail

# ---- ajuste estas 3 linhas se os nomes/caminhos mudarem ----
APP_DIR="/home/ec2-user/app"
COMPOSE_FILE="$APP_DIR/docker-compose.prod.yml"
S3_BUCKET="__S3_BUCKET__"   # substitua pelo output "s3_backup_bucket" do terraform
# --------------------------------------------------------------

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

cd "$APP_DIR"

# Carrega DATABASE_URL do .env (sem exportar o arquivo inteiro)
DATABASE_URL=$(grep -E '^DATABASE_URL=' .env | cut -d= -f2-)

echo "[$TIMESTAMP] Gerando dump do Postgres..."
# Usa um container temporário com o cliente do Postgres (a imagem da API
# não tem pg_dump instalado — só a lib psycopg2 pra falar com o banco).
docker run --rm postgres:16-alpine \
  pg_dump "$DATABASE_URL" | gzip > "$TMP_DIR/db_${TIMESTAMP}.sql.gz"

echo "[$TIMESTAMP] Compactando uploads..."
docker run --rm \
  -v bpo-system_uploads_data:/uploads:ro \
  -v "$TMP_DIR":/backup \
  alpine sh -c "tar -czf /backup/uploads_${TIMESTAMP}.tar.gz -C /uploads ."

echo "[$TIMESTAMP] Enviando pro S3..."
aws s3 cp "$TMP_DIR/db_${TIMESTAMP}.sql.gz" "s3://${S3_BUCKET}/db/db_${TIMESTAMP}.sql.gz"
aws s3 cp "$TMP_DIR/uploads_${TIMESTAMP}.tar.gz" "s3://${S3_BUCKET}/uploads/uploads_${TIMESTAMP}.tar.gz"

echo "[$TIMESTAMP] Backup concluído: db_${TIMESTAMP}.sql.gz e uploads_${TIMESTAMP}.tar.gz"
