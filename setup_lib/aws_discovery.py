"""AWS resource discovery via boto3 or AWS CLI."""

import json
import os
import subprocess

from setup_lib import constants


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
                        if constants.OIDC_FEDERATION in str(fed):
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
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
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
            if constants.OIDC_FEDERATION in str(fed):
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
