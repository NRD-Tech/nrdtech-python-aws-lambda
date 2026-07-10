#########################################################
# Cost / resource grouping tags + AWS Resource Groups
#
# Tags (applied to all resources via provider default_tags):
#   Environment - staging | prod          → Cost Explorer by env
#   Repository  - this git repository     → Cost Explorer by repo
#   Project     - product spanning repos  → Cost Explorer by project
#
# Resource Groups (console browsing):
#   rg-{Repository}-{Environment}         → always created (owned by this stack)
#   rg-project-{Project}-{Environment}    → created when MANAGE_PROJECT_RESOURCE_GROUP=true
#     (set true on exactly one repo per Project+Environment to avoid name conflicts)
#########################################################

locals {
  project_name = var.PROJECT_NAME != "" ? var.PROJECT_NAME : var.APP_IDENT_WITHOUT_ENV

  common_tags = {
    Environment = var.ENVIRONMENT
    Repository  = var.APP_IDENT_WITHOUT_ENV
    Project     = local.project_name
  }

  manage_project_resource_group = (
    var.MANAGE_PROJECT_RESOURCE_GROUP == "true" ||
    (var.MANAGE_PROJECT_RESOURCE_GROUP == "" && local.project_name == var.APP_IDENT_WITHOUT_ENV)
  )
}

resource "aws_resourcegroups_group" "repository_environment" {
  name        = "rg-${var.APP_IDENT_WITHOUT_ENV}-${var.ENVIRONMENT}"
  description = "Resources for repository ${var.APP_IDENT_WITHOUT_ENV} in ${var.ENVIRONMENT}"

  resource_query {
    query = jsonencode({
      ResourceTypeFilters = ["AWS::AllSupported"]
      TagFilters = [
        {
          Key    = "Repository"
          Values = [var.APP_IDENT_WITHOUT_ENV]
        },
        {
          Key    = "Environment"
          Values = [var.ENVIRONMENT]
        }
      ]
    })
  }
}

resource "aws_resourcegroups_group" "project_environment" {
  count = local.manage_project_resource_group ? 1 : 0

  name        = "rg-project-${local.project_name}-${var.ENVIRONMENT}"
  description = "Resources for project ${local.project_name} in ${var.ENVIRONMENT}"

  resource_query {
    query = jsonencode({
      ResourceTypeFilters = ["AWS::AllSupported"]
      TagFilters = [
        {
          Key    = "Project"
          Values = [local.project_name]
        },
        {
          Key    = "Environment"
          Values = [var.ENVIRONMENT]
        }
      ]
    })
  }
}
