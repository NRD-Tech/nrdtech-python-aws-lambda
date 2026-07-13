"""Interactive prompt helpers."""

import sys

from setup_lib import constants
from setup_lib.config_io import detect_current_app_type


def _choose_from_list(prompt_msg, items, allow_custom=True):
    if not items:
        return input(f"{prompt_msg}: ").strip()
    print(prompt_msg)
    for i, x in enumerate(items, 1):
        label = x.get("arn") or x.get("name") or str(x) if isinstance(x, dict) else str(x)
        print(f"  {i}: {label}")
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
    return not s or s == constants.TERRAFORM_STATE_BUCKET_PLACEHOLDER


def _is_placeholder_role(arn):
    a = (arn or "").strip()
    return not a or constants.AWS_ROLE_ARN_PLACEHOLDER_ACCOUNT in a


def _effective(current, key, placeholder_check=None):
    val = current.get(key, "")
    if placeholder_check and placeholder_check(val):
        return ""
    return val or ""


def prompt(msg, default=""):
    if default:
        s = input(f"{msg} [{default}]: ").strip()
        return s if s else default
    while True:
        s = input(f"{msg}: ").strip()
        if s:
            return s


def prompt_yes_no(msg, default_no=True):
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    s = input(msg + suffix).strip().lower()
    if not s:
        return not default_no
    return s in ("y", "yes")


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
    if not getattr(args, "project_name", ""):
        args.project_name = prompt(
            "Project name (shared across related repos for cost grouping)",
            current.get("project_name", "") or args.app_name,
        )
    if not getattr(args, "manage_project_resource_group", ""):
        default_mgr = current.get("manage_project_resource_group", "")
        if not default_mgr:
            default_mgr = "true" if args.project_name == args.app_name else "false"
        args.manage_project_resource_group = prompt(
            "Manage project Resource Group? (true/false — true on one repo per project)",
            default_mgr,
        )

    if not args.app_type:
        detected = detect_current_app_type()
        args.app_type = prompt("App type ({})".format(" | ".join(constants.APP_TYPES)), detected)
        if args.app_type not in constants.APP_TYPES:
            print(f"Invalid app type '{args.app_type}'. Defaulting to 'scheduled'.", file=sys.stderr)
            args.app_type = "scheduled"

    for attr, default in [
        ("app_timeout", current.get("app_timeout", "60")),
        ("app_memory", current.get("app_memory", "128")),
        ("cpu_architecture", current.get("cpu_architecture", "X86_64")),
    ]:
        if not getattr(args, attr):
            setattr(args, attr, default)

    if args.app_type == "api":
        if not args.api_root_domain and discovered["route53_domains"]:
            args.api_root_domain = _choose_from_list("API root domain (Route53):", discovered["route53_domains"])
        if not args.api_root_domain:
            args.api_root_domain = prompt(
                "API root domain (must exist in Route53)", current.get("api_root_domain", "example.com")
            )
        if not args.api_domain_staging:
            args.api_domain_staging = prompt(
                "API domain for staging", current.get("api_domain_staging", "api-staging." + args.api_root_domain)
            )
        if not args.api_domain_prod:
            args.api_domain_prod = prompt(
                "API domain for prod", current.get("api_domain_prod", "api." + args.api_root_domain)
            )
