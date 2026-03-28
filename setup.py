#!/usr/bin/env python3
"""
Setup for AWS Lambda (Python) template.
Configures app type (api | sqs_triggered | scheduled),
config.global / config.staging / config.prod, Terraform trigger files, and the active handler.
Auto-discovers OIDC role, Terraform state bucket, and Route53 domains.

Run from project root:  python3 setup.py [--app-type ...] [options]
Works on macOS and Windows (Python 3.6+). Safe to re-run.
"""

from __future__ import print_function

import argparse
import json
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_MAIN = os.path.join(SCRIPT_DIR, "terraform", "main")
APP_DIR = os.path.join(SCRIPT_DIR, "app")
GITHUB_WORKFLOWS = os.path.join(SCRIPT_DIR, ".github", "workflows")
CONFIG_GLOBAL = os.path.join(SCRIPT_DIR, "config.global")
CONFIG_STAGING = os.path.join(SCRIPT_DIR, "config.staging")
CONFIG_PROD = os.path.join(SCRIPT_DIR, "config.prod")

APP_TYPES = ("api", "sqs_triggered", "scheduled")

TRIGGER_TYPE_MAP = {
    "api": "api_gateway",
    "sqs_triggered": "sqs",
    "scheduled": "scheduled",
}
TRIGGER_TYPE_REVERSE = {v: k for k, v in TRIGGER_TYPE_MAP.items()}
# Legacy aliases
TRIGGER_TYPE_REVERSE["api_gateway"] = "api"
TRIGGER_TYPE_REVERSE["eventbridge"] = "scheduled"

TF_FILE_BY_TYPE = {
    "api": "lambda_api_gateway.tf",
    "sqs_triggered": "lambda_sqs_trigger.tf",
    "scheduled": "lambda_eventbridge_schedule.tf",
}

HANDLER_FILE_BY_TYPE = {
    "api": "lambda_handler_api_gateway.py.disabled",
    "sqs_triggered": "lambda_handler_sqs.py.disabled",
    "scheduled": "lambda_handler_eventbridge.py.disabled",
}

OIDC_FEDERATION = "token.actions.githubusercontent.com"
TERRAFORM_STATE_BUCKET_PLACEHOLDER = "mycompany-terraform-state"
AWS_ROLE_ARN_PLACEHOLDER_ACCOUNT = "1234567890"


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------
def _parse_export_file(path):
    """Parse shell ``export KEY=value`` lines into a dict (quotes stripped)."""
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


def read_current_config():
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


def detect_current_app_type():
    """Return which app type is active (which .tf file has uncommented resources)."""
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


# ---------------------------------------------------------------------------
# AWS credentials
# ---------------------------------------------------------------------------
def _has_credentials():
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True
    if os.environ.get("AWS_PROFILE"):
        return True
    creds_path = os.path.expanduser(os.path.join("~", ".aws", "credentials"))
    if os.path.isfile(creds_path):
        with open(creds_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() == "[default]":
                    return True
    return False


def prompt_for_aws_credentials():
    print("\nAWS credentials (used to discover Terraform bucket, OIDC role, etc.)")
    choice = input("Use (1) AWS profile or (2) access key/secret? [1]: ").strip() or "1"
    if choice == "2":
        key = input("AWS_ACCESS_KEY_ID: ").strip()
        secret = input("AWS_SECRET_ACCESS_KEY: ").strip()
        if key:
            os.environ["AWS_ACCESS_KEY_ID"] = key
        if secret:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret
        os.environ.pop("AWS_PROFILE", None)
    else:
        profile = input("AWS profile name: ").strip()
        if profile:
            os.environ["AWS_PROFILE"] = profile
        os.environ.pop("AWS_ACCESS_KEY_ID", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)


def ensure_aws_credentials():
    if _has_credentials():
        return
    print("No AWS credentials found (AWS_PROFILE, AWS_ACCESS_KEY_ID/SECRET, or ~/.aws/credentials [default]).", file=sys.stderr)
    print("Run without --non-interactive to be prompted, or export credentials first.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# AWS resource discovery (boto3 preferred, CLI fallback)
# ---------------------------------------------------------------------------
def _try_boto3_discover(region):
    out = {"oidc_roles": [], "terraform_buckets": [], "route53_domains": []}
    try:
        import boto3
    except ImportError:
        return out
    try:
        session = boto3.Session(region_name=region)
        iam = session.client("iam")
        for page in iam.get_paginator("list_roles").paginate():
            for role in page.get("Roles", []):
                name = role.get("RoleName")
                arn = role.get("Arn", "")
                try:
                    doc = iam.get_role(RoleName=name).get("Role", {}).get("AssumeRolePolicyDocument", {})
                    for s in doc.get("Statement", []):
                        fed = (s.get("Principal") or {}).get("Federated") or ""
                        if isinstance(fed, list):
                            fed = " ".join(fed)
                        if OIDC_FEDERATION in str(fed):
                            out["oidc_roles"].append({"arn": arn, "name": name})
                            break
                except Exception:
                    pass
    except Exception:
        pass
    try:
        s3 = session.client("s3")
        for b in s3.list_buckets().get("Buckets", []):
            name = b.get("Name", "")
            if "terraform" in name.lower():
                out["terraform_buckets"].append(name)
    except Exception:
        pass
    try:
        r53 = session.client("route53")
        for zone in r53.list_hosted_zones().get("HostedZones", []):
            name = zone.get("Name", "").rstrip(".")
            if name:
                out["route53_domains"].append(name)
    except Exception:
        pass
    return out


def _run_aws_cli(cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            env={**os.environ, "AWS_DEFAULT_OUTPUT": "json"},
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return {}


def _try_cli_discover(region):
    out = {"oidc_roles": [], "terraform_buckets": [], "route53_domains": []}
    data = _run_aws_cli(["aws", "iam", "list-roles", "--max-items", "100"])
    for role in data.get("Roles", []):
        arn = role.get("Arn", "")
        name = role.get("RoleName", "")
        if not name:
            continue
        detail = _run_aws_cli(["aws", "iam", "get-role", "--role-name", name])
        doc = (detail.get("Role") or {}).get("AssumeRolePolicyDocument") or {}
        for s in doc.get("Statement", []):
            fed = (s.get("Principal") or {}).get("Federated") or ""
            if OIDC_FEDERATION in str(fed):
                out["oidc_roles"].append({"arn": arn, "name": name})
                break
    for b in _run_aws_cli(["aws", "s3api", "list-buckets"]).get("Buckets", []):
        name = b.get("Name", "")
        if name and "terraform" in name.lower():
            out["terraform_buckets"].append(name)
    for z in _run_aws_cli(["aws", "route53", "list-hosted-zones"]).get("HostedZones", []):
        name = (z.get("Name") or "").rstrip(".")
        if name:
            out["route53_domains"].append(name)
    return out


def discover_aws_resources(region):
    discovered = _try_boto3_discover(region)
    if not discovered["oidc_roles"] and not discovered["terraform_buckets"]:
        discovered = _try_cli_discover(region)
    return discovered


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def _choose_from_list(prompt_msg, items, allow_custom=True):
    if not items:
        return input("{}: ".format(prompt_msg)).strip()
    print(prompt_msg)
    for i, x in enumerate(items, 1):
        label = x.get("arn") or x.get("name") or str(x) if isinstance(x, dict) else str(x)
        print("  {}: {}".format(i, label))
    if allow_custom:
        print("  0: Enter value manually")
    choice = input("Choice [1]: ").strip() or "1"
    try:
        idx = int(choice)
        if idx == 0 and allow_custom:
            return input("Value: ").strip()
        if 1 <= idx <= len(items):
            x = items[idx - 1]
            return x.get("arn") if isinstance(x, dict) and "arn" in x else str(x)
    except ValueError:
        pass
    return choice


def _is_placeholder_bucket(name):
    s = (name or "").strip()
    return not s or s == TERRAFORM_STATE_BUCKET_PLACEHOLDER


def _is_placeholder_role(arn):
    a = (arn or "").strip()
    return not a or AWS_ROLE_ARN_PLACEHOLDER_ACCOUNT in a


def _effective(current, key, placeholder_check=None):
    val = current.get(key, "")
    if placeholder_check and placeholder_check(val):
        return ""
    return val or ""


def prompt(msg, default=""):
    if default:
        s = input("{} [{}]: ".format(msg, default)).strip()
        return s if s else default
    while True:
        s = input("{}: ".format(msg)).strip()
        if s:
            return s


def prompt_yes_no(msg, default_no=True):
    default = "n" if default_no else "y"
    s = input("{} [{}]: ".format(msg, default)).strip().lower()
    if not s:
        return not default_no
    return s in ("y", "yes")


# ---------------------------------------------------------------------------
# Terraform comment/uncomment helpers
# ---------------------------------------------------------------------------
def _looks_like_terraform_code(line):
    rest = line.strip()
    if not rest or rest in ("{", "}"):
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
        "rulePriority ", "selection ", "countNumber ", "description ", "tags ",
    )
    if any(rest.startswith(p) for p in tf_prefixes):
        return True
    if rest.startswith("=") or " = " in rest:
        return True
    if line.startswith("# ") and len(line) > 2 and line[2] in " \t":
        return True
    return False


def uncomment_tf_file(path):
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


def comment_tf_file(path):
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


def ensure_tf_commented(tf_name):
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


# ---------------------------------------------------------------------------
# Config writers
# ---------------------------------------------------------------------------
def write_config_global(args):
    content = """\
#########################################################
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
export AWS_ROLE_ARN={aws_role_arn}
export AWS_WEB_IDENTITY_TOKEN_FILE=$(pwd)/web-identity-token

# Lambda timeout and memory settings
export APP_TIMEOUT={app_timeout}  # seconds
export APP_MEMORY={app_memory}  # memory in MB

# Must be one of these: X86_64, ARM64
# NOTE: Only GitHub supports ARM64 builds - Bitbucket doesn't
export CPU_ARCHITECTURE={cpu_architecture}

#########################################################
# Create code hash
#########################################################
export CODE_HASH_FILE=code_hash.txt
docker run --rm -v $(pwd):/workdir -w /workdir alpine sh -c \\
  "apk add --no-cache findutils coreutils && \\
   find . -type f -path './.git*' -prune -o -path './.github*' -prune -o \\( -name '*.py' -o -name '*.sh' -o -name 'Dockerfile' -o -name 'pyproject.toml' -o -name 'poetry.lock' -o -name 'config.*' \\) \\
   -exec md5sum {{}} + | sort | md5sum | cut -d ' ' -f1 > terraform/main/${{CODE_HASH_FILE}}"
"""
    with open(CONFIG_GLOBAL, "w", encoding="utf-8") as f:
        f.write(content.format(
            app_name=args.app_name,
            terraform_state_bucket=args.terraform_state_bucket,
            aws_region=args.aws_region,
            aws_role_arn=args.aws_role_arn,
            app_timeout=args.app_timeout,
            app_memory=args.app_memory,
            cpu_architecture=args.cpu_architecture,
        ))
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
    with open(CONFIG_STAGING, "w", encoding="utf-8") as f:
        f.write(content.format(
            api_root_domain=getattr(args, "api_root_domain", "example.com"),
            api_domain_staging=getattr(args, "api_domain_staging", "api-staging.example.com"),
        ))
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
    with open(CONFIG_PROD, "w", encoding="utf-8") as f:
        f.write(content.format(
            api_root_domain=getattr(args, "api_root_domain", "example.com"),
            api_domain_prod=getattr(args, "api_domain_prod", "api.example.com"),
        ))
    print("Wrote config.prod")


# ---------------------------------------------------------------------------
# Project-specific: Terraform & handler
# ---------------------------------------------------------------------------
def configure_terraform(app_type):
    for tf_name in TF_FILE_BY_TYPE.values():
        ensure_tf_commented(tf_name)
    tf_name = TF_FILE_BY_TYPE[app_type]
    path = os.path.join(TERRAFORM_MAIN, tf_name)
    uncomment_tf_file(path)
    print("Uncommented terraform/main/{}".format(tf_name))


def configure_handler(app_type):
    src_name = HANDLER_FILE_BY_TYPE[app_type]
    src = os.path.join(APP_DIR, src_name)
    dst = os.path.join(APP_DIR, "lambda_handler.py")
    if not os.path.isfile(src):
        print("Warning: {} not found; skipping handler setup".format(src_name))
        return
    shutil.copy2(src, dst)
    print("Created app/lambda_handler.py from {}".format(src_name))


def enable_github_workflow():
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


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------
def _prompt_common(args, current, discovered):
    eff_role = _effective(current, "aws_role_arn", _is_placeholder_role)
    eff_bucket = _effective(current, "terraform_state_bucket", _is_placeholder_bucket)

    if not args.aws_role_arn:
        if eff_role:
            args.aws_role_arn = eff_role
        elif discovered["oidc_roles"]:
            args.aws_role_arn = _choose_from_list("OIDC role (GitHub Actions):", discovered["oidc_roles"])
        else:
            args.aws_role_arn = prompt("OIDC role ARN", eff_role)

    if not args.terraform_state_bucket:
        if eff_bucket:
            args.terraform_state_bucket = eff_bucket
        elif discovered["terraform_buckets"]:
            args.terraform_state_bucket = _choose_from_list("Terraform state bucket:", discovered["terraform_buckets"])
        else:
            args.terraform_state_bucket = prompt("Terraform state bucket", eff_bucket)

    if not args.app_name:
        args.app_name = prompt("App name (APP_IDENT_WITHOUT_ENV, max 20 chars)", current.get("app_name", ""))

    if not args.app_type:
        detected = detect_current_app_type()
        args.app_type = prompt("App type ({})".format(" | ".join(APP_TYPES)), detected)
        if args.app_type not in APP_TYPES:
            print("Invalid app type '{}'. Defaulting to 'scheduled'.".format(args.app_type), file=sys.stderr)
            args.app_type = "scheduled"

    for attr, default in [
        ("app_timeout", current.get("app_timeout", "60")),
        ("app_memory", current.get("app_memory", "128")),
        ("cpu_architecture", current.get("cpu_architecture", "X86_64")),
        ("aws_region", current.get("aws_region", "us-west-2")),
    ]:
        if not getattr(args, attr):
            setattr(args, attr, default)

    if args.app_type == "api":
        if not args.api_root_domain and discovered["route53_domains"]:
            args.api_root_domain = _choose_from_list("API root domain (Route53):", discovered["route53_domains"])
        if not args.api_root_domain:
            args.api_root_domain = prompt("API root domain (must exist in Route53)", current.get("api_root_domain", "example.com"))
        if not args.api_domain_staging:
            args.api_domain_staging = prompt("API domain for staging", current.get("api_domain_staging", "api-staging." + args.api_root_domain))
        if not args.api_domain_prod:
            args.api_domain_prod = prompt("API domain for prod", current.get("api_domain_prod", "api." + args.api_root_domain))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Configure this AWS Lambda (Python) project.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--app-type", choices=APP_TYPES, help="api | sqs_triggered | scheduled")
    parser.add_argument("--app-name", default="", help="APP_IDENT_WITHOUT_ENV (max 20 chars)")
    parser.add_argument("--terraform-state-bucket", default="", help="S3 bucket for Terraform state")
    parser.add_argument("--aws-region", default="us-west-2", help="AWS region")
    parser.add_argument("--aws-role-arn", default="", help="OIDC deployment role ARN")
    parser.add_argument("--app-timeout", default="60", help="Lambda timeout (seconds)")
    parser.add_argument("--app-memory", default="128", help="Lambda memory (MB)")
    parser.add_argument("--cpu-architecture", default="X86_64", choices=("X86_64", "ARM64"))
    parser.add_argument("--api-root-domain", default="", help="Root domain for API (api type only)")
    parser.add_argument("--api-domain-staging", default="", help="API domain for staging")
    parser.add_argument("--api-domain-prod", default="", help="API domain for prod")
    parser.add_argument("--enable-github-workflow", action="store_true", help="Enable github_flow.yml")
    parser.add_argument("--non-interactive", action="store_true", help="Fail if required args missing")
    args = parser.parse_args()

    current = read_current_config()

    if not args.non_interactive:
        prompt_for_aws_credentials()
    ensure_aws_credentials()

    region = args.aws_region or current.get("aws_region", "us-west-2")
    discovered = discover_aws_resources(region)
    if discovered["oidc_roles"] or discovered["terraform_buckets"] or discovered["route53_domains"]:
        print("Discovered AWS resources (you can select by number or enter manually).")

    if args.non_interactive:
        for attr, desc in [("app_name", "App name"), ("terraform_state_bucket", "Terraform state bucket"), ("aws_role_arn", "OIDC role ARN")]:
            if not getattr(args, attr):
                print("Error: {} required. Set --{} or run without --non-interactive.".format(desc, attr.replace("_", "-")), file=sys.stderr)
                return 1
        if not args.app_type:
            print("Error: --app-type required when using --non-interactive", file=sys.stderr)
            return 1
        if args.app_type not in APP_TYPES:
            print("Error: invalid app type '{}'".format(args.app_type), file=sys.stderr)
            return 1
        defaults = {"app_timeout": "60", "app_memory": "128", "cpu_architecture": "X86_64"}
        for attr, default in defaults.items():
            if not getattr(args, attr):
                setattr(args, attr, current.get(attr, default))
        if args.app_type == "api":
            args.api_root_domain = args.api_root_domain or current.get("api_root_domain", "example.com")
            args.api_domain_staging = args.api_domain_staging or current.get("api_domain_staging", "api-staging.example.com")
            args.api_domain_prod = args.api_domain_prod or current.get("api_domain_prod", "api.example.com")
    else:
        _prompt_common(args, current, discovered)

    write_config_global(args)
    write_config_staging(args)
    write_config_prod(args)
    configure_terraform(args.app_type)
    configure_handler(args.app_type)

    workflow_path = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml")
    if not args.non_interactive and not args.enable_github_workflow and not os.path.isfile(workflow_path):
        if prompt_yes_no("Enable GitHub workflow?", default_no=True):
            args.enable_github_workflow = True
    if args.enable_github_workflow:
        enable_github_workflow()

    print("Setup complete. Edit config.global (and config.staging/config.prod) if needed, then deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
