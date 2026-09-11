FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

# ENVIRONMENT=production (definido via docker-compose/.env) desativa
# o --reload; qualquer outro valor (ou ausência) mantém o
# comportamento de desenvolvimento de antes.
ENV ENVIRONMENT=development

CMD ["./docker-entrypoint.sh"]