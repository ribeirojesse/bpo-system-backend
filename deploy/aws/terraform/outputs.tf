output "ec2_public_ip" {
  description = "IP público da EC2 (Elastic IP se enable_elastic_ip=true, senão o IP dinâmico da instância)"
  value       = var.enable_elastic_ip ? aws_eip.api[0].public_ip : aws_instance.api.public_ip
}

output "ec2_ssh_command" {
  description = "Comando pra conectar via SSH"
  value       = "ssh ec2-user@${var.enable_elastic_ip ? aws_eip.api[0].public_ip : aws_instance.api.public_ip}"
}

output "rds_endpoint" {
  description = "Endpoint do RDS (host:porta) — use pra montar a DATABASE_URL"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "Só o host do RDS, sem a porta"
  value       = aws_db_instance.postgres.address
}

output "database_url" {
  description = "DATABASE_URL pronta pra colar no .env da EC2 (a senha some do output do terraform, mas fica salva no state — trate o state como segredo)"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  sensitive   = true
}

output "s3_backup_bucket" {
  description = "Nome do bucket S3 de backup"
  value       = aws_s3_bucket.backups.bucket
}
