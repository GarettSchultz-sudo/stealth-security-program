# ClawShell Infrastructure - Main Terraform Configuration
# This configuration deploys the complete ClawShell stack to AWS

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "clawshell-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "clawshell-terraform-locks"
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ClawShell"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "https://github.com/GarettSchultz-sudo/stealth-security-program"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "clawshell"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "ecs_instance_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}

variable "ecs_cpu" {
  description = "CPU units for ECS tasks"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "Memory for ECS tasks (MB)"
  type        = number
  default     = 2048
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.small"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the service"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Local values
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  name_prefix          = local.name_prefix
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

  tags = local.common_tags
}

# Security Groups
module "security_groups" {
  source = "./modules/security_groups"

  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id

  allowed_cidr_blocks = var.allowed_cidr_blocks

  tags = local.common_tags
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  name_prefix         = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.security_groups.db_security_group_id

  instance_class     = var.db_instance_class
  database_name      = "clawshell"
  database_username  = "clawshell_admin"

  tags = local.common_tags
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"

  name_prefix         = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.security_groups.redis_security_group_id

  node_type = var.redis_node_type

  tags = local.common_tags
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"

  name_prefix         = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  alb_security_group_id   = module.security_groups.alb_security_group_id
  ecs_security_group_id   = module.security_groups.ecs_security_group_id

  cpu       = var.ecs_cpu
  memory    = var.ecs_memory
  task_count = var.ecs_instance_count

  db_connection_string = module.rds.connection_string
  redis_connection_string = module.redis.connection_string

  tags = local.common_tags
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix

  tags = local.common_tags
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"

  name_prefix = local.name_prefix

  db_password = module.rds.master_password

  tags = local.common_tags
}

# CloudWatch
module "cloudwatch" {
  source = "./modules/cloudwatch"

  name_prefix = local.name_prefix

  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_name = module.ecs.service_name

  tags = local.common_tags
}

# Outputs
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.ecs.alb_dns_name
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "https://${module.ecs.alb_dns_name}"
}

output "db_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecs.ecr_repository_url
}
