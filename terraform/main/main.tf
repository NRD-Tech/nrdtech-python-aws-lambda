terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81.0"
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
# VPC
#############################
# Custom VPC
# locals {
#   vpc_name = "my-standard-vpc"
# }
# data "aws_vpc" "selected" {
#   filter {
#     name   = "tag:Name"
#     values = [local.vpc_name]
#   }
# }

# Default VPC
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
data "aws_route_tables" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }

  filter {
    name   = "association.subnet-id"
    values = data.aws_subnets.private.ids
  }
}
