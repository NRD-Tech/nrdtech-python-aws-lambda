# Application Bootstrap
# - The purpose of this script is to create the AWS Application so that all resources made
#   in the main terraform can be associated with this application using the application tag.
# - By tagging them into an Application we are able to easily see the infrastructure costs
#   associated with this project
# - This needs to happen before the rest of the terraform resources are created so that we
#   can tag everything correctly

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.81.0"
    }
  }
}

variable "AWS_REGION" {
  type = string
}

variable "APP_IDENT" {
  description = "Identifier of the application"
  type        = string
}

provider "aws" {
  alias  = "app_registration"
  region = var.AWS_REGION
}

resource "aws_servicecatalogappregistry_application" "app" {
  provider = aws.app_registration
  name     = var.APP_IDENT
}

output "app_tags" {
  value = aws_servicecatalogappregistry_application.app.application_tag
}
