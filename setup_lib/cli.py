"""CLI entry for project setup."""

import argparse
import os
import sys

from setup_lib import constants
from setup_lib.apply_templates import configure_handler, configure_terraform
from setup_lib.aws_creds import (
    ensure_aws_credentials,
    prompt_for_aws_credentials,
    resolve_aws_region,
)
from setup_lib.aws_discovery import discover_aws_resources
from setup_lib.config_io import (
    read_current_config,
    write_config_global,
    write_config_prod,
    write_config_staging,
)
from setup_lib.github_gating import (
    configure_github_protections,
    enable_github_workflow,
    resolve_github_approval_settings,
)
from setup_lib.prompts import _prompt_common, prompt, prompt_yes_no


def main():
    parser = argparse.ArgumentParser(
        description="Configure this AWS Lambda (Python) project.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--app-type", choices=constants.APP_TYPES, help="api | sqs_triggered | scheduled")
    parser.add_argument("--app-name", default="", help="APP_IDENT_WITHOUT_ENV (max 20 chars)")
    parser.add_argument(
        "--project-name", default="", help="Project name for cross-repo cost grouping (defaults to app-name)"
    )
    parser.add_argument(
        "--manage-project-resource-group",
        default="",
        choices=("", "true", "false"),
        help="Create rg-project-* Resource Group (true on one repo per project)",
    )
    parser.add_argument("--terraform-state-bucket", default="", help="S3 bucket for Terraform state")
    parser.add_argument("--aws-region", default="", help="AWS region (defaults to profile/env detection)")
    parser.add_argument("--aws-role-arn", default="", help="OIDC deployment role ARN")
    parser.add_argument("--app-timeout", default="60", help="Lambda timeout (seconds)")
    parser.add_argument("--app-memory", default="128", help="Lambda memory (MB)")
    parser.add_argument("--cpu-architecture", default="X86_64", choices=("X86_64", "ARM64"))
    parser.add_argument("--api-root-domain", default="", help="Root domain for API (api type only)")
    parser.add_argument("--api-domain-staging", default="", help="API domain for staging")
    parser.add_argument("--api-domain-prod", default="", help="API domain for prod")
    parser.add_argument("--github-org", default="", help="GitHub org for plan detection / protections")
    parser.add_argument(
        "--github-approval-mode",
        default="",
        choices=("",) + constants.APPROVAL_MODES,
        help="dispatch (Team default) or environment (Enterprise Environment reviewers)",
    )
    parser.add_argument("--enable-github-workflow", action="store_true", help="Enable github_flow.yml")
    parser.add_argument(
        "--configure-github-protections", action="store_true", help="Create Environments + main ruleset via gh"
    )
    parser.add_argument("--non-interactive", action="store_true", help="Fail if required args missing")
    args = parser.parse_args()

    current = read_current_config()

    if not args.non_interactive:
        prompt_for_aws_credentials()
    ensure_aws_credentials()

    args.aws_region = resolve_aws_region(args.aws_region, current)
    if not args.non_interactive:
        args.aws_region = prompt("AWS region", args.aws_region)

    discovered = discover_aws_resources(args.aws_region)
    if discovered["oidc_roles"] or discovered["terraform_buckets"] or discovered["route53_domains"]:
        print("Discovered AWS resources (you can select by number or enter manually).")

    if args.non_interactive:
        for attr, desc in [
            ("app_name", "App name"),
            ("terraform_state_bucket", "Terraform state bucket"),
            ("aws_role_arn", "OIDC role ARN"),
        ]:
            if not getattr(args, attr):
                print(
                    "Error: {} required. Set --{} or run without --non-interactive.".format(
                        desc, attr.replace("_", "-")
                    ),
                    file=sys.stderr,
                )
                return 1
        if not args.app_type:
            print("Error: --app-type required when using --non-interactive", file=sys.stderr)
            return 1
        if args.app_type not in constants.APP_TYPES:
            print(f"Error: invalid app type '{args.app_type}'", file=sys.stderr)
            return 1
        if not getattr(args, "project_name", ""):
            args.project_name = current.get("project_name", "") or args.app_name
        if not getattr(args, "manage_project_resource_group", ""):
            args.manage_project_resource_group = current.get("manage_project_resource_group", "") or (
                "true" if args.project_name == args.app_name else "false"
            )
        defaults = {"app_timeout": "60", "app_memory": "128", "cpu_architecture": "X86_64"}
        for attr, default in defaults.items():
            if not getattr(args, attr):
                setattr(args, attr, current.get(attr, default))
        if args.app_type == "api":
            args.api_root_domain = args.api_root_domain or current.get("api_root_domain", "example.com")
            args.api_domain_staging = args.api_domain_staging or current.get(
                "api_domain_staging", "api-staging.example.com"
            )
            args.api_domain_prod = args.api_domain_prod or current.get("api_domain_prod", "api.example.com")
    else:
        _prompt_common(args, current, discovered)

    gh, org, mode, plan = resolve_github_approval_settings(args, current, args.non_interactive)
    print("Using GITHUB_APPROVAL_MODE={}{}".format(mode, f" (org plan={plan})" if plan else ""))

    write_config_global(args)
    write_config_staging(args)
    write_config_prod(args)
    configure_terraform(args.app_type)
    configure_handler(args.app_type)

    if not args.non_interactive and not args.enable_github_workflow and not os.path.isfile(constants.WORKFLOW_ENABLED):
        if prompt_yes_no("Enable GitHub workflow?", default_no=True):
            args.enable_github_workflow = True
    if args.enable_github_workflow:
        enable_github_workflow()

    if args.configure_github_protections or (
        not args.non_interactive
        and prompt_yes_no("Configure GitHub Environments + main PR ruleset via gh?", default_no=True)
    ):
        configure_github_protections(gh, org, mode, args.non_interactive)

    print("Setup complete. Edit config.global (and config.staging/config.prod) if needed, then deploy.")
    print("CI: plan runs automatically; apply is gated (dispatch Run workflow, or Environment approval).")
    return 0
