"""Config file parsing and writers."""

import os

from setup_lib import constants


def _parse_export_file(path):
    """Parse shell ``export KEY=value`` lines into a dict (quotes stripped)."""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("export ") or "=" not in line:
                continue
            rest = line[7:].strip()
            key, _, val = rest.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                out[key] = val
    return out


def read_current_config():
    current = {}
    g = _parse_export_file(constants.CONFIG_GLOBAL)
    if g:
        current["app_name"] = g.get("APP_IDENT_WITHOUT_ENV", "")
        current["project_name"] = g.get("PROJECT_NAME", "") or g.get("APP_IDENT_WITHOUT_ENV", "")
        current["manage_project_resource_group"] = g.get("MANAGE_PROJECT_RESOURCE_GROUP", "")
        current["terraform_state_bucket"] = g.get("TERRAFORM_STATE_BUCKET", "")
        current["aws_region"] = g.get("AWS_DEFAULT_REGION", "us-west-2")
        current["aws_role_arn"] = g.get("AWS_ROLE_ARN", "")
        current["app_timeout"] = g.get("APP_TIMEOUT", "60")
        current["app_memory"] = g.get("APP_MEMORY", "128")
        current["cpu_architecture"] = g.get("CPU_ARCHITECTURE", "X86_64")
        current["github_approval_mode"] = g.get("GITHUB_APPROVAL_MODE", constants.DEFAULT_APPROVAL_MODE)
        current["github_org"] = g.get("GITHUB_ORG", "")
    s = _parse_export_file(constants.CONFIG_STAGING)
    if s:
        current["api_root_domain"] = s.get("API_ROOT_DOMAIN", "")
        current["api_domain_staging"] = s.get("API_DOMAIN", "")
    p = _parse_export_file(constants.CONFIG_PROD)
    if p:
        current["api_domain_prod"] = p.get("API_DOMAIN", "")
    return current


def detect_current_app_type():
    """Return app type from config trigger_type, falling back to scheduled."""
    g = _parse_export_file(constants.CONFIG_GLOBAL)
    raw = g.get("trigger_type", "eventbridge")
    return constants.TRIGGER_TYPE_REVERSE.get(raw, "scheduled")


def write_config_global(args):
    project_name = getattr(args, "project_name", "") or args.app_name
    manage_project_rg = getattr(args, "manage_project_resource_group", "")
    if not manage_project_rg:
        manage_project_rg = "true" if project_name == args.app_name else "false"
    trigger = constants.TRIGGER_TYPE_MAP.get(args.app_type, "eventbridge")
    github_org = getattr(args, "github_org", "") or ""
    approval_mode = getattr(args, "github_approval_mode", "") or constants.DEFAULT_APPROVAL_MODE
    content = """\
#########################################################
# Configuration
#########################################################
# Used to identify this repository in AWS resources | allowed characters: a-zA-Z0-9-_
# NOTE: This must be no longer than 20 characters long
# Also used as the Repository cost-allocation tag
export APP_IDENT_WITHOUT_ENV={app_name}
export APP_IDENT="${{APP_IDENT_WITHOUT_ENV}}-${{ENVIRONMENT}}"
export TERRAFORM_STATE_IDENT=$APP_IDENT

# Project name for cross-repository cost/resource grouping (Cost Explorer tag: Project).
# Use the same PROJECT_NAME on related repos (e.g. backend + frontend).
export PROJECT_NAME={project_name}

# When true, this stack creates rg-project-{{PROJECT_NAME}}-{{ENVIRONMENT}}.
# Set true on exactly one repo per Project+Environment (usually the "primary" repo).
export MANAGE_PROJECT_RESOURCE_GROUP={manage_project_resource_group}

# This is the AWS S3 bucket in which you are storing your terraform state files
# - This must exist before deploying
export TERRAFORM_STATE_BUCKET={terraform_state_bucket}

# This is the AWS region in which the application will be deployed
export AWS_DEFAULT_REGION={aws_region}
export AWS_REGION=${{AWS_DEFAULT_REGION}}

# OIDC Deployment role
export AWS_ROLE_ARN={aws_role_arn}
export AWS_WEB_IDENTITY_TOKEN_FILE=$(pwd)/web-identity-token

# GitHub Actions deploy gating (see .github/workflows/github_flow.yml)
#   dispatch    — Team-safe default: plan on push/release; apply via workflow_dispatch
#   environment — Enterprise: apply jobs wait on Environment required reviewers
export GITHUB_ORG={github_org}
export GITHUB_APPROVAL_MODE={github_approval_mode}

# Optional: email for CloudWatch alarm SNS subscription (prod)
# export ALERT_EMAIL=ops@example.com


# Lambda timeout and memory settings
export APP_TIMEOUT={app_timeout}  # seconds
export APP_MEMORY={app_memory}  # memory in MB

# Must be one of these: X86_64, ARM64
# NOTE: Only GitHub supports ARM64 builds - Bitbucket doesn't
export CPU_ARCHITECTURE={cpu_architecture}

# Lambda trigger type: api_gateway | sqs | eventbridge
# All trigger .tf files stay active; count conditions gate which resources are created.
export trigger_type={trigger_type}

#########################################################
# Create code hash
#########################################################
export CODE_HASH_FILE=code_hash.txt
docker run --rm -v $(pwd):/workdir -w /workdir alpine sh -c \\
  "apk add --no-cache findutils coreutils && \\
   find . -type f -path './.git*' -prune -o -path './.github*' -prune -o \\( -name '*.py' -o -name '*.sh' -o -name 'Dockerfile' -o -name 'pyproject.toml' -o -name 'poetry.lock' -o -name 'config.*' \\) \\
   -exec md5sum {{}} + | sort | md5sum | cut -d ' ' -f1 > terraform/main/${{CODE_HASH_FILE}}"
"""
    with open(constants.CONFIG_GLOBAL, "w", encoding="utf-8") as f:
        f.write(
            content.format(
                app_name=args.app_name,
                project_name=project_name,
                manage_project_resource_group=manage_project_rg,
                terraform_state_bucket=args.terraform_state_bucket,
                aws_region=args.aws_region,
                aws_role_arn=args.aws_role_arn,
                github_org=github_org,
                github_approval_mode=approval_mode,
                app_timeout=args.app_timeout,
                app_memory=args.app_memory,
                cpu_architecture=args.cpu_architecture,
                trigger_type=trigger,
            )
        )
    print("Wrote config.global")


def write_config_staging(args):
    if args.app_type == "api":
        api_block = """\

####################################################################################################
# API Gateway Settings (only needed for app type 'api')
# * The root domain MUST already exist in Route53 in your AWS account
####################################################################################################
export API_ROOT_DOMAIN={api_root_domain}
export API_DOMAIN={api_domain_staging}
"""
    else:
        api_block = """\

####################################################################################################
# API Gateway (unused when app type is not 'api'; leave as placeholder)
####################################################################################################
export API_ROOT_DOMAIN=example.com
export API_DOMAIN=api-staging.example.com
"""
    content = "# NOTE: Variables set in here will activate only in a staging environment\n" + api_block
    with open(constants.CONFIG_STAGING, "w", encoding="utf-8") as f:
        f.write(
            content.format(
                api_root_domain=getattr(args, "api_root_domain", "example.com"),
                api_domain_staging=getattr(args, "api_domain_staging", "api-staging.example.com"),
            )
        )
    print("Wrote config.staging")


def write_config_prod(args):
    if args.app_type == "api":
        api_block = """\

####################################################################################################
# API Gateway Settings (only needed for app type 'api')
####################################################################################################
export API_ROOT_DOMAIN={api_root_domain}
export API_DOMAIN={api_domain_prod}
"""
    else:
        api_block = """\

####################################################################################################
# API Gateway (unused when app type is not 'api')
####################################################################################################
export API_ROOT_DOMAIN=example.com
export API_DOMAIN=api.example.com
"""
    content = "# NOTE: Variables set in here will activate only in a production environment\n" + api_block
    with open(constants.CONFIG_PROD, "w", encoding="utf-8") as f:
        f.write(
            content.format(
                api_root_domain=getattr(args, "api_root_domain", "example.com"),
                api_domain_prod=getattr(args, "api_domain_prod", "api.example.com"),
            )
        )
    print("Wrote config.prod")
