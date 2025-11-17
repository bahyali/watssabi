resource "aws_ecr_repository" "app" {
  name                 = replace(local.name_prefix, "_", "-")
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-ecr"
  })
}
