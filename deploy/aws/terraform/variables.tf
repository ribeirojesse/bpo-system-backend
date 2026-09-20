variable "aws_region" {
  description = "Região AWS. sa-east-1 (São Paulo) tem menor latência pro Brasil e também é elegível pro free tier."
  type        = string
  default     = "sa-east-1"
}

variable "project_name" {
  description = "Prefixo usado no nome de todos os recursos criados."
  type        = string
  default     = "bpo-system"
}

variable "ec2_instance_type" {
  description = "Tipo da instância EC2. t3.micro é free tier na maioria das regiões; em regiões antigas pode ser t2.micro."
  type        = string
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "Classe da instância RDS. db.t3.micro é free tier (750h/mês nos primeiros 12 meses, conta clássica)."
  type        = string
  default     = "db.t3.micro"
}

variable "db_engine_version" {
  description = "Versão do Postgres no RDS."
  type        = string
  default     = "16" # so a versao maior — a AWS escolhe a minor mais recente disponivel na regiao
}

variable "db_allocated_storage" {
  description = "Armazenamento do RDS em GB. Free tier cobre até 20GB gp3/gp2."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Nome do banco (mesmo do docker-compose local: bpo_db)."
  type        = string
  default     = "bpo_db"
}

variable "db_username" {
  description = "Usuário master do RDS."
  type        = string
  default     = "bpo_admin"
}

variable "db_password" {
  description = "Senha master do RDS. NÃO deixe um valor default em produção — passe via terraform.tfvars (fora do git) ou variável de ambiente TF_VAR_db_password."
  type        = string
  sensitive   = true
}

variable "my_ip_cidr" {
  description = "Seu IP público, em formato CIDR (ex: 200.150.10.20/32), liberado pra SSH na porta 22. Descubra o seu em https://checkip.amazonaws.com"
  type        = string
}

variable "ssh_public_key" {
  description = "Conteúdo da sua chave pública SSH (ex: cat ~/.ssh/id_ed25519.pub), usada pra criar o key pair da EC2."
  type        = string
}

variable "allowed_origins" {
  description = "Domínio(s) do frontend liberado(s) no CORS da API, separados por vírgula (ex: https://app.seudominio.com)."
  type        = string
  default     = "http://localhost:5173"
}

variable "enable_elastic_ip" {
  description = "Se true, associa um Elastic IP fixo à instância (recomendado — o IP público comum muda se a instância reiniciar). Em conta free tier clássica isso continua dentro das 750h grátis de IPv4 enquanted anexado a uma instância rodando."
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "E-mail que recebe alerta de custo (AWS Budgets) quando o gasto do mês passa 80% do limite, e uma previsão de estourar 100%. Deixe em branco (\"\") pra não criar o budget — mas em conta nova (crédito, sem free tier mensal fixo) é fortemente recomendado preencher."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  description = "Limite mensal (USD) usado só pra disparar o alerta por e-mail — não bloqueia nem desliga nada automaticamente, é aviso mesmo."
  type        = number
  default     = 10
}
