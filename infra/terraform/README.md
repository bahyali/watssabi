# AWS Terraform Deployment

Infrastructure-as-code definitions for running the Watssabi AI Collector application on AWS. The configuration provisions a containerized FastAPI service on ECS Fargate behind an Application Load Balancer, along with managed PostgreSQL (RDS) and Redis (ElastiCache) instances.

## What Gets Created

- Dedicated VPC with public and private subnets across two Availability Zones
- Internet/NAT gateways and routing tables
- Security groups restricting traffic between the load balancer, ECS tasks, RDS, and Redis
- Elastic Container Registry (ECR) repository for application images
- ECS Fargate cluster, task definition, service, and CloudWatch log group
- Application Load Balancer and target group
- RDS PostgreSQL instance and subnet group
- ElastiCache Redis cluster and subnet group

## Prerequisites

- Terraform CLI v1.5 or newer
- AWS account credentials with permissions to create the above resources
- Docker (to build and push the application image)

## Usage

1. Change into the Terraform directory:

   ```bash
   cd infra/terraform
   ```

2. Initialize Terraform:

   ```bash
   terraform init
   ```

3. Create a `terraform.tfvars` file (or supply variables another way) with the required values. A starting point:

   ```hcl
   aws_region          = "us-east-1"
   project_name        = "watssabi-ai-collector"
   environment         = "dev"
   db_username         = "watssabi_user"
   db_password         = "change_me"
   openai_api_key      = "sk-..."
   twilio_account_sid  = "AC..."
   twilio_auth_token   = "your_twilio_auth_token"
   twilio_phone_number = "whatsapp:+14155238886"
   ```

   By default the ECS task will expect an image tagged `latest` in the ECR repository that this configuration creates. If you prefer to use an existing image, set `container_image` to a fully-qualified image URI.

4. Apply the configuration:

   ```bash
   terraform apply
   ```

   Review the plan carefully, then confirm to create the infrastructure.

5. Build and push the Docker image (only required if you rely on the managed ECR repository):

   ```bash
   AWS_REGION="us-east-1" # match the aws_region variable
   AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ECR_URL=$(terraform output -raw ecr_repository_url)
   docker build -t "${ECR_URL}:latest" ../..
   aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URL"
   docker push "${ECR_URL}:latest"
   ```

   After the image push completes, ECS will pull the new image according to the deployment configuration.

## Configuration Notes

- `allowed_alb_ingress_cidrs` defaults to `0.0.0.0/0`. Restrict it for production deployments.
- `extra_env_vars` lets you inject additional container environment variables beyond the defaults derived from RDS/Redis credentials.
- The RDS instance enables storage encryption and retains seven days of backups. Modify `db_allocated_storage`, `db_instance_class`, and retention settings to meet your workload and compliance requirements.
- The ElastiCache cluster provisions a single-node Redis instance suitable for development or staging workloads. Scale up the node type or move to replication groups for production.

## Cleanup

To tear everything down, run:

```bash
terraform destroy
```

Always confirm that the generated plan only removes resources you no longer need.
