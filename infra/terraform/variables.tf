variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
}

variable "project_name" {
  description = "Human readable project name used in tagging."
  type        = string
  default     = "watssabi-ai-collector"
}

variable "environment" {
  description = "Deployment environment name (e.g. dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "allowed_alb_ingress_cidrs" {
  description = "CIDR blocks allowed to access the public load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "container_image" {
  description = "Full container image URI. Leave null to use the provisioned ECR repository."
  type        = string
  default     = null
}

variable "container_image_tag" {
  description = "Image tag used when pushing to the provisioned ECR repository."
  type        = string
  default     = "latest"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of desired ECS service tasks."
  type        = number
  default     = 2
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "health_check_path" {
  description = "HTTP path used by the load balancer to check container health."
  type        = string
  default     = "/health"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (must align with availability zones)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (must align with availability zones)."
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "db_username" {
  description = "Master username for the PostgreSQL instance."
  type        = string
}

variable "db_password" {
  description = "Master password for the PostgreSQL instance."
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Default database name for the application."
  type        = string
  default     = "watssabi_db"
}

variable "db_instance_class" {
  description = "Instance type for RDS PostgreSQL."
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for RDS."
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "RDS PostgreSQL engine version."
  type        = string
  default     = "15.4"
}

variable "redis_node_type" {
  description = "Node type for the ElastiCache Redis cluster."
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_engine_version" {
  description = "Redis engine version."
  type        = string
  default     = "7.1"
}

variable "openai_api_key" {
  description = "OpenAI API key passed to the application."
  type        = string
  sensitive   = true
}

variable "twilio_account_sid" {
  description = "Twilio Account SID used by the application."
  type        = string
  sensitive   = true
}

variable "twilio_auth_token" {
  description = "Twilio Auth Token used by the application."
  type        = string
  sensitive   = true
}

variable "twilio_phone_number" {
  description = "Twilio WhatsApp-enabled phone number (e.g. whatsapp:+14155238886)."
  type        = string
}

variable "extra_env_vars" {
  description = "Additional environment variables for the container."
  type        = map(string)
  default     = {}
}
