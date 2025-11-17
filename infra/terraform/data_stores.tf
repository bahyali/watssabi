resource "aws_db_subnet_group" "postgres" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-db-subnets"
  })
}

resource "aws_db_instance" "postgres" {
  identifier              = "${local.name_prefix}-postgres"
  engine                  = "postgres"
  engine_version          = var.db_engine_version
  instance_class          = var.db_instance_class
  username                = var.db_username
  password                = var.db_password
  db_name                 = var.db_name
  allocated_storage       = var.db_allocated_storage
  storage_encrypted       = true
  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  apply_immediately       = true
  multi_az                = false
  publicly_accessible     = false
  vpc_security_group_ids  = [aws_security_group.db.id]
  db_subnet_group_name    = aws_db_subnet_group.postgres.name

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-redis-subnets"
  })
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = replace("${local.name_prefix}-redis", "_", "-")
  engine               = "redis"
  engine_version       = var.redis_engine_version
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  maintenance_window   = "sun:05:00-sun:06:00"
  parameter_group_name = "default.redis7"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-redis"
  })
}
