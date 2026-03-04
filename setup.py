#!/usr/bin/env python3
"""
Setup for AWS Lambda (Python) template. Configures app type (api_gateway | sqs | scheduled),
config.global / config.staging / config.prod, Terraform trigger files, and the active handler.
Run from the project root: python3 setup.py [--app-type api_gateway|sqs|scheduled] [options]
Works on macOS and Windows (Python 3.6+).

Safe to re-run: if config.global (and staging/prod) already exist, their values are used
as defaults so you can press Enter to keep them or change only what you need.
"""

from __future__ import print_function

import argparse
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_MAIN = os.path.join(SCRIPT_DIR, "terraform", "main")
APP_DIR = os.path.join(SCRIPT_DIR, "app")
GITHUB_WORKFLOWS = os.path.join(SCRIPT_DIR, ".github", "workflows")
CONFIG_GLOBAL = os.path.join(SCRIPT_DIR, "config.global")
CONFIG_STAGING = os.path.join(SCRIPT_DIR, "config.staging")
CONFIG_PROD = os.path.join(SCRIPT_DIR, "config.prod")

APP_TYPES = ("api_gateway", "sqs", "scheduled")

TF_FILE_BY_TYPE = {
    "api_gateway": "lambda_api_gateway.tf",
    "sqs": "lambda_sqs_trigger.tf",
    "scheduled": "lambda_eventbridge_schedule.tf",
}

HANDLER_FILE_BY_TYPE = {
    "api_gateway": "lambda_handler_api_gateway.py.disabled",
    "sqs": "lambda_handler_sqs.py.disabled",
    "scheduled": "lambda_handler_eventbridge.py.disabled",
}


def _parse_export_file(path: str) -> dict:
    """Parse shell export KEY=value lines; return dict of KEY -> value (quotes stripped)."""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
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


def read_current_config() -> dict:
    """Read existing config.global (and staging/prod) into a flat dict for use as defaults."""
    current = {}
    g = _parse_export_file(CONFIG_GLOBAL)
    if g:
        current["app_name"] = g.get("APP_IDENT_WITHOUT_ENV", "")
        current["terraform_state_bucket"] = g.get("TERRAFORM_STATE_BUCKET", "")
        current["aws_region"] = g.get("AWS_DEFAULT_REGION", "us-west-2")
        current["aws_role_arn"] = g.get("AWS_ROLE_ARN", "")
        current["app_timeout"] = g.get("APP_TIMEOUT", "60")
        current["app_memory"] = g.get("APP_MEMORY", "128")
        current["cpu_architecture"] = g.get("CPU_ARCHITECTURE", "X86_64")
    s = _parse_export_file(CONFIG_STAGING)
    if s:
        current["api_root_domain"] = s.get("API_ROOT_DOMAIN", "")
        current["api_domain_staging"] = s.get("API_DOMAIN", "")
    p = _parse_export_file(CONFIG_PROD)
    if p:
        current["api_domain_prod"] = p.get("API_DOMAIN", "")
    return current


def detect_current_app_type() -> str:
    """Return which app type is active (which type-specific .tf has uncommented resource)."""
    for app_type, tf_name in TF_FILE_BY_TYPE.items():
        path = os.path.join(TERRAFORM_MAIN, tf_name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            if any(
                line.strip().startswith(("resource ", "data ", "output "))
                for line in f
                if line.strip()
            ):
                return app_type
    return "scheduled"


def _looks_like_terraform_code(line: str) -> bool:
    """True if the line (without '# ') is Terraform code, not a comment."""
    rest = line.strip()
    if not rest or rest == "{" or rest == "}":
        return True
    tf_prefixes = (
        "resource ", "data ", "output ", "variable ", "module ", "template ", "locals ",
        "aws_api_gateway", "aws_sqs", "aws_lambda", "aws_scheduler", "aws_iam", "aws_cloudwatch",
        "aws_ecr", "aws_route53", "aws_acm", "name ", "image ", "region ", "uri ", "arn ",
        "value ", "policy ", "role ", "statement ", "action ", "effect ", "principal ",
        "schedule_expression ", "target ", "flexible_time_window ", "state ", "batch_size ",
        "event_source_arn ", "function_name ", "enabled ", "environment ", "variables ",
        "rest_api_id ", "resource_id ", "http_method ", "integration_http_method ",
        "depends_on ", "endpoint_configuration ", "types ", "parent_id ", "path_part ",
        "authorization ", "type ", "integration ", "statement_id ", "source_arn ",
        "deployment_id ", "stage_name ", "domain_name ", "certificate_arn ", "zone_id ",
        "alias ", "response_parameters ", "request_templates ", "status_code ",
        "visibility_timeout_seconds ", "redrive_policy ", "maximum_batching_window ",
        "provisioner ", "triggers ", "policy_arn ", "assume_role_policy ", "countType ",
        "rulePriority ", "selection ", "countNumber ", "action ", "description ", "tags ",
    )
    if any(rest.startswith(p) for p in tf_prefixes):
        return True
    if rest.startswith("=") or " = " in rest:
        return True
    if line.startswith("# ") and len(line) > 2 and line[2] in " \t":
        return True
    return False


def uncomment_tf_file(path: str) -> None:
    """Uncomment a Terraform file: strip leading '# ' only from lines that are Terraform code."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    for line in lines:
        if line.startswith("# "):
            rest = line[2:]
            out.append(rest if _looks_like_terraform_code(rest) else line)
        elif line.strip() == "#":
            out.append("\n")
        else:
            out.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def comment_tf_file(path: str) -> None:
    """Comment every non-empty line so the file is fully commented (for re-run)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s or line.startswith("#"):
            out.append(line)
        else:
            out.append("# " + line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(out)


def ensure_tf_commented(tf_name: str) -> None:
    """Ensure the given .tf file is fully commented (so we can safely uncomment one)."""
    path = os.path.join(TERRAFORM_MAIN, tf_name)
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    has_active = any(
        line.strip().startswith(("resource ", "data ", "output "))
        for line in lines
        if line.strip()
    )
    if has_active:
        comment_tf_file(path)


def write_config_global(args: argparse.Namespace) -> None:
    content = """#########################################################
# Configuration
#########################################################
# Used to identify the application in AWS resources | allowed characters: a-zA-Z0-9-_
# NOTE: This must be no longer than 20 characters long
export APP_IDENT_WITHOUT_ENV={app_name}
export APP_IDENT="${{APP_IDENT_WITHOUT_ENV}}-${{ENVIRONMENT}}"
export TERRAFORM_STATE_IDENT=$APP_IDENT

# This is the AWS S3 bucket in which you are storing your terraform state files
# - This must exist before deploying
export TERRAFORM_STATE_BUCKET={terraform_state_bucket}

# This is the AWS region in which the application will be deployed
export AWS_DEFAULT_REGION={aws_region}

# OIDC Deployment role
# NOTE: for GitHub deployment you must also set this in the .github/workflows file
export AWS_ROLE_ARN={aws_role_arn}
export AWS_WEB_IDENTITY_TOKEN_FILE=$(pwd)/web-identity-token

# Lambda timeout and memory settings
export APP_TIMEOUT={app_timeout}
export APP_MEMORY={app_memory}

# Must be one of these: X86_64, ARM64
# NOTE: Only GitHub supports ARM64 builds - Bitbucket doesn't
export CPU_ARCHITECTURE={cpu_architecture}

#########################################################
# Create code hash
#########################################################
export CODE_HASH_FILE=code_hash.txt
docker run --rm -v $(pwd):/workdir -w /workdir alpine sh -c \\
  "apk add --no-cache findutils coreutils && \\
   find . -type f -path './.git*' -prune -o -path './.github*' -prune -o \\( -name '*.py' -o -name '*.sh' -o -name 'Dockerfile' -o -name 'pyproject.toml' -o -name 'poetry.lock' -o -name '.env.*' \\) \\
   -exec md5sum {{}} + | sort | md5sum | cut -d ' ' -f1 > terraform/main/{code_hash_placeholder}"
"""
    path = os.path.join(SCRIPT_DIR, "config.global")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.format(
            app_name=args.app_name,
            terraform_state_bucket=args.terraform_state_bucket,
            aws_region=args.aws_region,
            aws_role_arn=args.aws_role_arn,
            app_timeout=args.app_timeout,
            app_memory=args.app_memory,
            cpu_architecture=args.cpu_architecture,
            code_hash_placeholder="${CODE_HASH_FILE}",
        ))
    print("Wrote config.global")


def write_config_staging(args: argparse.Namespace) -> None:
    api_block = ""
    if args.app_type == "api_gateway":
        api_block = """
####################################################################################################
# API Gateway Settings
# * You only need these if you are triggering your lambda function from API Gateway
# * NOTE: The root domain MUST already exist in Route53 in your AWS account for this to work
####################################################################################################
export API_ROOT_DOMAIN={api_root_domain}
export API_DOMAIN={api_domain_staging}
"""
    else:
        api_block = """
####################################################################################################
# API Gateway (unused when app type is not api_gateway; leave as placeholder or override in deploy)
####################################################################################################
export API_ROOT_DOMAIN=example.com
export API_DOMAIN=api-staging.example.com
"""
    content = """# NOTE: Variables set in here will activate only in a staging environment
""" + api_block
    path = os.path.join(SCRIPT_DIR, "config.staging")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.format(
            api_root_domain=getattr(args, "api_root_domain", "example.com"),
            api_domain_staging=getattr(args, "api_domain_staging", "api-staging.example.com"),
        ))
    print("Wrote config.staging")


def write_config_prod(args: argparse.Namespace) -> None:
    api_block = ""
    if args.app_type == "api_gateway":
        api_block = """
####################################################################################################
# API Gateway Settings
####################################################################################################
export API_ROOT_DOMAIN={api_root_domain}
export API_DOMAIN={api_domain_prod}
"""
    else:
        api_block = """
####################################################################################################
# API Gateway (unused when app type is not api_gateway)
####################################################################################################
export API_ROOT_DOMAIN=example.com
export API_DOMAIN=api.example.com
"""
    content = """# NOTE: Variables set in here will activate only in a production environment
""" + api_block
    path = os.path.join(SCRIPT_DIR, "config.prod")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.format(
            api_root_domain=getattr(args, "api_root_domain", "example.com"),
            api_domain_prod=getattr(args, "api_domain_prod", "api.example.com"),
        ))
    print("Wrote config.prod")


def configure_terraform(app_type: str) -> None:
    for tf_name in TF_FILE_BY_TYPE.values():
        ensure_tf_commented(tf_name)
    tf_name = TF_FILE_BY_TYPE[app_type]
    path = os.path.join(TERRAFORM_MAIN, tf_name)
    uncomment_tf_file(path)
    print("Uncommented terraform/main/{}".format(tf_name))


def configure_handler(app_type: str) -> None:
    src_name = HANDLER_FILE_BY_TYPE[app_type]
    src = os.path.join(APP_DIR, src_name)
    dst = os.path.join(APP_DIR, "lambda_handler.py")
    if not os.path.isfile(src):
        print("Warning: {} not found; skipping handler setup".format(src_name))
        return
    shutil.copy2(src, dst)
    print("Created app/lambda_handler.py from {}".format(src_name))


def enable_github_workflow() -> None:
    disabled = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml.disabled")
    enabled = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml")
    if os.path.isfile(disabled):
        with open(disabled, "r", encoding="utf-8") as f:
            content = f.read()
        with open(enabled, "w", encoding="utf-8") as f:
            f.write(content)
        os.remove(disabled)
        print("Enabled GitHub Actions workflow: github_flow.yml")
    elif os.path.isfile(enabled):
        print("GitHub workflow already enabled")
    else:
        print("Warning: github_flow.yml.disabled not found")


def prompt(msg: str, default: str = "") -> str:
    if default:
        s = input("{} [{}]: ".format(msg, default)).strip()
        return s if s else default
    while True:
        s = input("{}: ".format(msg)).strip()
        if s:
            return s


def prompt_yes_no(msg: str, default_no: bool = True) -> bool:
    default = "n" if default_no else "y"
    s = input("{} [{}]: ".format(msg, default)).strip().lower()
    if not s:
        return not default_no
    return s in ("y", "yes")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure this AWS Lambda (Python) project for app type and AWS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--app-type",
        choices=APP_TYPES,
        help="App type: api_gateway (HTTP via API Gateway), sqs (SQS trigger), scheduled (EventBridge schedule)",
    )
    parser.add_argument("--app-name", default="", help="APP_IDENT_WITHOUT_ENV (max 20 chars)")
    parser.add_argument("--terraform-state-bucket", default="", help="S3 bucket for Terraform state")
    parser.add_argument("--aws-region", default="us-west-2", help="AWS region")
    parser.add_argument("--aws-role-arn", default="", help="OIDC deployment role ARN for CI/CD")
    parser.add_argument("--app-timeout", default="60", help="Lambda timeout (seconds)")
    parser.add_argument("--app-memory", default="128", help="Lambda memory (MB)")
    parser.add_argument("--cpu-architecture", default="X86_64", choices=("X86_64", "ARM64"))
    parser.add_argument(
        "--api-root-domain",
        default="",
        help="Root domain for API (api_gateway type only; must exist in Route53)",
    )
    parser.add_argument("--api-domain-staging", default="", help="API domain for staging (api_gateway only)")
    parser.add_argument("--api-domain-prod", default="", help="API domain for prod (api_gateway only)")
    parser.add_argument(
        "--enable-github-workflow",
        action="store_true",
        help="Rename github_flow.yml.disabled to github_flow.yml",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail if required args are missing instead of prompting",
    )
    args = parser.parse_args()

    current = read_current_config()
    detected_type = detect_current_app_type()
    parser_defaults = {
        "app_name": "",
        "terraform_state_bucket": "",
        "aws_region": "us-west-2",
        "aws_role_arn": "",
        "app_timeout": "60",
        "app_memory": "128",
        "cpu_architecture": "X86_64",
        "api_root_domain": "",
        "api_domain_staging": "",
        "api_domain_prod": "",
    }
    for attr, default_val in parser_defaults.items():
        attr_key = attr.replace("-", "_")
        if hasattr(args, attr_key) and current.get(attr_key) and getattr(args, attr_key) == default_val:
            setattr(args, attr_key, current[attr_key])

    if not args.app_type:
        if args.non_interactive:
            print("Error: --app-type required when using --non-interactive", file=sys.stderr)
            return 1
        print("App type: api_gateway (HTTP), sqs (SQS trigger), scheduled (EventBridge cron)")
        args.app_type = prompt("App type", detected_type)
        if args.app_type not in APP_TYPES:
            print("Invalid app type", file=sys.stderr)
            return 1

    required = [
        ("--app-name", "app_name", "APP_IDENT_WITHOUT_ENV (e.g. my-lambda-app)"),
        ("--terraform-state-bucket", "terraform_state_bucket", "S3 Terraform state bucket"),
        ("--aws-role-arn", "aws_role_arn", "OIDC deployment role ARN for CI/CD"),
    ]
    for flag, attr, desc in required:
        attr_key = attr.replace("-", "_")
        if args.non_interactive:
            if not getattr(args, attr_key):
                print("Error: {} required. Set {} or run without --non-interactive.".format(desc, flag), file=sys.stderr)
                return 1
        else:
            default = getattr(args, attr_key) or current.get(attr_key, "")
            setattr(args, attr_key, prompt(desc, default))

    if args.app_type == "api_gateway":
        api_prompts = [
            ("--api-root-domain", "api_root_domain", "API root domain (must exist in Route53; e.g. mydomain.com)", "mydomain.com"),
            ("--api-domain-staging", "api_domain_staging", "API domain for staging (e.g. api-staging.mydomain.com)", "api-staging.mydomain.com"),
            ("--api-domain-prod", "api_domain_prod", "API domain for prod (e.g. api.mydomain.com)", "api.mydomain.com"),
        ]
        for _flag, attr, desc, fallback in api_prompts:
            if args.non_interactive:
                if not getattr(args, attr, ""):
                    setattr(args, attr, fallback)
            else:
                default = getattr(args, attr, "") or current.get(attr, fallback)
                setattr(args, attr, prompt(desc, default or fallback))

    workflow_enabled_path = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml")
    if not args.non_interactive and not args.enable_github_workflow and not os.path.isfile(workflow_enabled_path):
        if prompt_yes_no("Enable GitHub workflow?", default_no=True):
            args.enable_github_workflow = True

    write_config_global(args)
    write_config_staging(args)
    write_config_prod(args)
    configure_terraform(args.app_type)
    configure_handler(args.app_type)

    if args.enable_github_workflow:
        enable_github_workflow()

    print("Setup complete. Next: edit config.global (and config.staging/config.prod) with your real values if needed, then deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
