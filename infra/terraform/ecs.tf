locals {
  ecs_container_image = coalesce(
    var.container_image,
    "${aws_ecr_repository.app.repository_url}:${var.container_image_tag}"
  )

  ecs_env_vars = merge(
    {
      PROJECT_NAME        = var.project_name
      POSTGRES_SERVER     = aws_db_instance.postgres.address
      POSTGRES_PORT       = tostring(aws_db_instance.postgres.port)
      POSTGRES_DB         = var.db_name
      POSTGRES_USER       = var.db_username
      POSTGRES_PASSWORD   = var.db_password
      REDIS_HOST          = aws_elasticache_cluster.redis.cache_nodes[0].address
      REDIS_PORT          = tostring(aws_elasticache_cluster.redis.port)
      OPENAI_API_KEY      = var.openai_api_key
      TWILIO_ACCOUNT_SID  = var.twilio_account_sid
      TWILIO_AUTH_TOKEN   = var.twilio_auth_token
      TWILIO_PHONE_NUMBER = var.twilio_phone_number
    },
    var.extra_env_vars
  )
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ecs/${local.name_prefix}"
  retention_in_days = 30

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-logs"
  })
}

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.tags
}

resource "aws_lb" "app" {
  name               = substr("${local.name_prefix}-alb", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for subnet in aws_subnet.public : subnet.id]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-alb"
  })
}

resource "aws_lb_target_group" "app" {
  name        = substr("${local.name_prefix}-tg", 0, 32)
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 3
    unhealthy_threshold = 3
    matcher             = "200-399"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-tg"
  })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = local.tags
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-task"
  cpu                      = tostring(var.task_cpu)
  memory                   = tostring(var.task_memory)
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = local.ecs_container_image
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      environment = [
        for k, v in local.ecs_env_vars : {
          name  = k
          value = v
        }
      ]
    }
  ])

  tags = local.tags
}

resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = [for subnet in aws_subnet.private : subnet.id]
    security_groups  = [aws_security_group.ecs_service.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-svc"
  })
}
