terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.0.2"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  default_tags {
    tags = data.terraform_remote_state.app_bootstrap.outputs.app_tags
  }
}

# Sometimes we specifically need us-east-1 for some resources
provider "aws" {
  alias  = "useast1"
  region = "us-east-1"
  default_tags {
    tags = data.terraform_remote_state.app_bootstrap.outputs.app_tags
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

#############################
# Default VPC
#############################
data "aws_vpc" "selected" {
  default = true
}
data "aws_subnets" "subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
}
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
  filter {
    name   = "tag:Name"
    values = ["*public*"]
  }
}
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
  filter {
    name   = "tag:Name"
    values = ["*private*"]
  }
}

#############################
# Custom VPC
#############################
# VPC
# variable "vpc_name" {
#   type = string
# }
# data "aws_vpc" "selected" {
#   filter {
#     name   = "tag:Name"
#     values = [var.vpc_name]
#   }
# }
# 
# # Subnets
# data "aws_subnet_ids" "all" {
#   vpc_id = data.aws_vpc.selected.id
# }
# data "aws_subnet_ids" "private" {
#   vpc_id = data.aws_vpc.selected.id
#   tags = {
#     Name = "*private*"
#   }
# }
# data "aws_subnet_ids" "public" {
#   vpc_id = data.aws_vpc.selected.id
#   tags = {
#     Name = "*public*"
#   }
# }
#######################################
