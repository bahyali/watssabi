output "vpc_id" {
  description = "ID of the created VPC."
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "DNS name of the application load balancer."
  value       = aws_lb.app.dns_name
}

output "alb_security_group_id" {
  description = "Security group ID associated with the load balancer."
  value       = aws_security_group.alb.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.app.name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository to push application images."
  value       = aws_ecr_repository.app.repository_url
}

output "db_endpoint" {
  description = "Endpoint address for the PostgreSQL instance."
  value       = aws_db_instance.postgres.address
}

output "redis_endpoint" {
  description = "Endpoint address for the Redis cluster."
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}
