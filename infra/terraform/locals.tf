locals {
  name_prefix = lower(replace("${var.project_name}-${var.environment}", " ", "-"))

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}
