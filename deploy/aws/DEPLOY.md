# Deploy do backend BPO System na AWS (free tier)

Arquitetura: 1 EC2 (roda a API em Docker) + 1 RDS PostgreSQL (substitui o
container `postgres` do compose local) + 1 bucket S3 (backups). Tudo na
VPC default da conta — sem NAT Gateway, sem Load Balancer, sem nenhum
componente extra que teria custo fixo por conta própria. Isso é o setup
mais enxuto possível pro free tier — mas leia a seção 0: **na sua conta
(criada depois de jul/2025) isso não fica em US$0**, fica dentro de um
crédito com prazo.

```
Internet ── HTTP/HTTPS (80/443) ──▶ EC2 (t3.micro, IP público)
                                       │  docker: container "bpo_api"
                                       │
                                       ▼ porta 5432, só da EC2 (security group)
                                     RDS PostgreSQL (t3.micro, SEM IP público)

EC2 (via IAM role, sem chave fixa) ──▶ S3 (backups: dump do banco + uploads)
```

## 0. Sua conta é nova — o que isso muda

Contas AWS criadas depois de 15/07/2025 (a sua é uma delas) não têm mais o
free tier clássico de 750h/mês por 12 meses. Em vez disso:

- Você ganha **US$100 em créditos** ao criar a conta, podendo chegar a
  **US$200** usando certos serviços (EC2 é um deles).
- Esse crédito vale por **6 meses a partir da criação da conta, ou até
  acabar o crédito — o que vier primeiro**.
- **Importante, e diferente do que muita gente pensa:** quando o crédito
  acaba ou os 6 meses passam, a AWS **não sai cobrando fatura
  automaticamente**. A conta é **fechada automaticamente** — você perde
  acesso aos recursos (a EC2 para, o site sai do ar) — e você tem 90 dias
  pra fazer upgrade manual pra um plano pago (1 clique no console) antes de
  tudo ser apagado de vez.
- Ou seja: o risco real pra você não é "conta de cartão surpresa", é **a
  API do BPO sair do ar sem aviso** se o crédito acabar e ninguém
  perceber. Como isso aqui não é um teste e sim o backend de um sistema
  real que seus clientes/equipe usam, vale já decidir se, quando o crédito
  acabar, você vai querer fazer o upgrade pra manter no ar (o Terraform
  aqui já entrega um alerta por e-mail em 80% do gasto pra te dar tempo de
  decidir — veja `alert_email` no `terraform.tfvars`).

**Confira seu saldo e data de expiração exatos em:** console AWS →
**Billing and Cost Management → Free Tier** (mostra o crédito restante e
quando expira).

**Estimativa de custo mensal deste setup, fora do crédito** (depois que
ele acabar, ou se você já quiser rodar num plano pago desde já) — valores
aproximados, região `sa-east-1` (São Paulo), consulte a [calculadora
oficial da AWS](https://calculator.aws) pro valor exato:

| Item | Estimativa/mês |
|---|---|
| EC2 t3.micro (750h) | ~US$11–13 |
| RDS db.t3.micro Single-AZ | ~US$19–22 |
| Armazenamento RDS (20GB gp3) | ~US$3 |
| Armazenamento EBS da EC2 (20GB gp3) | ~US$2 |
| IP público (Elastic IP anexado) | ~US$3,65 |
| S3 (backups, poucos GB) | < US$1 |
| **Total aproximado** | **~US$40–45/mês** |

Com US$100–200 de crédito, isso te dá tranquilamente uns **2 a 5 meses**
de runway, não os 6 meses inteiros — o crédito provavelmente acaba antes
do prazo. Duas formas de esticar isso, se fizer sentido pra você:
- Trocar `aws_region` pra `us-east-1` no `terraform.tfvars` — EC2/RDS lá
  costumam ser mais baratos que em `sa-east-1` (só que com mais latência
  pro Brasil, uns 150–200ms a mais por requisição).
- Rodar só durante horário comercial (parar EC2+RDS à noite/fim de semana)
  — reduz as horas cobradas, mas dá trabalho manual ou exige automação
  extra que este pacote não inclui.

De qualquer forma, **preencha `alert_email` no `terraform.tfvars`** antes
do `terraform apply` — isso cria um AWS Budget que te avisa por e-mail
quando o gasto do mês passar 80% do limite que você definir
(`monthly_budget_usd`, default US$10). O aviso não desliga nada sozinho,
mas te dá tempo de agir antes do crédito zerar e a conta fechar.

## 1. Pré-requisitos

Na sua máquina:

- AWS CLI instalado e configurado (`aws configure`) com um usuário IAM
  (não use a conta root) com permissão de administrador ou, pelo menos,
  EC2/RDS/S3/IAM/VPC.
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5.
- Uma chave SSH (`ssh-keygen -t ed25519 -C "bpo-system-aws"` se não tiver
  uma).

## 2. Provisionar a infraestrutura (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edite `terraform.tfvars`:
- `db_password`: uma senha forte (não a que está no `.env` de dev).
- `my_ip_cidr`: seu IP público + `/32`. Descubra em
  https://checkip.amazonaws.com
- `ssh_public_key`: conteúdo do seu `.pub` (ex.: `type
  $env:USERPROFILE\.ssh\id_ed25519.pub` no PowerShell, ou `cat
  ~/.ssh/id_ed25519.pub` no Git Bash/WSL).

Depois:

```bash
terraform init
terraform plan    # confira o que vai ser criado antes de aplicar
terraform apply
```

Isso leva uns 5–8 minutos (o RDS demora pra ficar disponível). No final,
anote os outputs:

```bash
terraform output ec2_public_ip
terraform output rds_endpoint
terraform output s3_backup_bucket
terraform output -raw database_url   # sensível: não cole isso em chat/print público
```

## 3. Colocar o código na EC2

Conecte via SSH (o comando exato sai em `terraform output ec2_ssh_command`):

```bash
ssh ec2-user@<ec2_public_ip>
mkdir -p ~/app   # o user_data já cria essa pasta, mas garante
exit
```

Envie o código do backend pra lá. Duas opções:

**Opção A — `scp` direto da sua máquina** (mais simples, não precisa de git remoto).
Rode no Git Bash/WSL/PowerShell com OpenSSH:

```bash
# 1. copia o código do backend inteiro (inclui coisas que não devem ir pra
#    produção — venv, .git, uploads de dev — por isso limpamos depois)
scp -r D:/00_DEV/00_Projetos/bpo-system/backend ec2-user@<ec2_public_ip>:~/app-raw

ssh ec2-user@<ec2_public_ip> '
  rsync -a --exclude venv --exclude .git --exclude uploads --exclude deploy \
    ~/app-raw/ ~/app/ 2>/dev/null || cp -r ~/app-raw/* ~/app/
  rm -rf ~/app-raw ~/app/venv ~/app/.git ~/app/uploads
'

# 2. copia os arquivos de produção deste pacote (docker-compose.prod.yml,
#    o script de backup e o template de .env) pra dentro de ~/app
scp D:/00_DEV/00_Projetos/bpo-system/backend/deploy/aws/docker-compose.prod.yml \
    ec2-user@<ec2_public_ip>:~/app/
scp D:/00_DEV/00_Projetos/bpo-system/backend/deploy/aws/env.production.example \
    ec2-user@<ec2_public_ip>:~/app/.env.production.example
ssh ec2-user@<ec2_public_ip> mkdir -p ~/app/scripts
scp D:/00_DEV/00_Projetos/bpo-system/backend/deploy/aws/scripts/backup_to_s3.sh \
    ec2-user@<ec2_public_ip>:~/app/scripts/
```

**Opção B — git clone**, se o backend já estiver num repositório (GitHub/GitLab):

```bash
ssh ec2-user@<ec2_public_ip>
git clone <url-do-seu-repositorio> app-src
mv app-src/* ~/app/ 2>/dev/null
rm -rf app-src ~/app/venv
```
(depois, repita o passo 2 acima pra copiar `docker-compose.prod.yml`,
`env.production.example` e `scripts/backup_to_s3.sh`)

## 4. Configurar o `.env` de produção

Na EC2, dentro de `~/app`:

```bash
cp .env.production.example .env
nano .env
```

Preencha:
- `DATABASE_URL`: monte com `rds_endpoint`/`rds_address` do terraform +
  usuário/senha que você definiu em `db_username`/`db_password` (ou cole
  direto o `terraform output -raw database_url`).
- `SECRET_KEY`: gere um novo com `openssl rand -hex 32` — **não** reuse o
  do ambiente de dev.
- `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`:
  copie os mesmos valores do `.env` de dev, se quiser manter o mesmo
  comportamento de expiração de sessão.
- `ENVIRONMENT=production` (isso desliga o `--reload` do uvicorn).
- `ALLOWED_ORIGINS`: domínio real do frontend em produção. Sem isso o
  navegador bloqueia as chamadas por CORS.

## 5. Subir os containers

```bash
cd ~/app
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f api   # Ctrl+C pra sair do log
```

## 6. Rodar as migrations (Alembic)

Primeira vez que o banco (RDS, vazio) recebe o schema:

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api alembic current   # deve mostrar "(head)"
```

## 7. Testar

```bash
curl http://<ec2_public_ip>/
# {"message":"API ONLINE"}
```

No navegador: `http://<ec2_public_ip>/docs` mostra o Swagger (considere
desativar isso depois em produção — ver seção 9).

## 8. Backups automáticos pro S3

Na EC2:

```bash
mkdir -p ~/app/scripts
# copie backup_to_s3.sh pra lá (scp ou colar) e ajuste S3_BUCKET
chmod +x ~/app/scripts/backup_to_s3.sh
crontab -e
```

Adicione uma linha pra rodar todo dia às 3h da manhã:

```
0 3 * * * /home/ec2-user/app/scripts/backup_to_s3.sh >> /home/ec2-user/backup.log 2>&1
```

## 9. Recomendações de segurança (baseado na auditoria do projeto)

Isso não é feito automaticamente por este pacote de deploy — são ajustes
no código/config que valem a pena antes de considerar isso "produção de
verdade":

- Trocar a senha padrão do fallback de `set_portal_access`
  (`Cliente@123`) por uma senha aleatória por cliente.
- Desativar `/docs` e `/openapi.json` em produção (`FastAPI(docs_url=None,
  redoc_url=None)` quando `ENVIRONMENT=production`).
- Mover o `token`/`refreshToken` do `localStorage` do frontend pra cookie
  `httpOnly` (reforço de defesa contra XSS).
- Quando o frontend também for pra produção: parar de usar
  `http://localhost:8000` fixo no `axios.js` (usar
  `VITE_API_URL`) e servir tudo via HTTPS.
- Quando tiver um domínio: colocar Nginx + Certbot na frente da API (porta
  443) em vez de expor HTTP puro na 80. A infraestrutura já libera a porta
  443 no security group pra isso.

## 10. Administrar o RDS sem expor a porta 5432

O banco não tem IP público (por isso não roda pgAdmin público como no
compose de dev). Pra acessar com um cliente local (DBeaver, pgAdmin
desktop, psql), abra um túnel SSH pela EC2:

```bash
ssh -L 5433:<rds_address>:5432 ec2-user@<ec2_public_ip>
```

E conecte seu cliente em `localhost:5433`.

## 11. Atualizar a aplicação depois de mudanças no código

```bash
# reenvie o código atualizado (scp ou git pull), depois:
cd ~/app
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head   # se houver migration nova
```

## 12. Desligar tudo (evitar qualquer cobrança)

```bash
cd terraform
terraform destroy
```

Confirme com `yes`. Isso apaga EC2, RDS, security groups e o S3 (o bucket
só é removido se estiver vazio — se tiver backups, esvazie antes com `aws
s3 rm s3://<bucket> --recursive` ou remova o bucket manualmente no
console).

## Referência rápida de custos (dentro dos limites deste setup)

| Recurso | Tamanho | Free tier clássico (conta < jul/2025) | Conta nova (crédito) |
|---|---|---|---|
| EC2 | 1x t3.micro | Grátis, 750h/mês por 12 meses | Cobrado, abatido do crédito |
| RDS | 1x db.t3.micro, 20GB | Grátis, 750h/mês + 20GB por 12 meses | Cobrado, abatido do crédito |
| S3 | backups, até 5GB | Grátis até 5GB | Cobrado, abatido do crédito |
| IP público (Elastic IP anexado à instância rodando) | 1 | Coberto pelas mesmas 750h/mês do EC2 | ~US$3,60/mês se não coberto por crédito |

Fontes consultadas sobre a mudança de política de free tier: [anúncio
oficial da AWS sobre o novo Free Tier de crédito + 6 meses](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/),
[documentação oficial sobre o que acontece quando o plano gratuito
termina](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html),
[AWS Free Tier em 2026 — o que continua grátis](https://dev.to/aiunplugged/aws-free-tier-in-2026-what-actually-stays-free-5bcp),
[Guia completo do Free Tier 2026](https://agentdeals.dev/aws-free-tier-2026),
[Cobrança de IPv4 público mesmo no free tier](https://repost.aws/articles/ARknH_OR0cTvqoTfJrVGaB8A/why-am-i-seeing-charges-for-public-ipv4-addresses-when-i-am-under-the-aws-free-tier).
