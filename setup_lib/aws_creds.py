"""AWS credential prompts and region detection."""

import os
import subprocess
import sys

from setup_lib import constants


def _has_credentials():
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True
    if os.environ.get("AWS_PROFILE"):
        return True
    creds_path = os.path.expanduser(os.path.join("~", ".aws", "credentials"))
    if os.path.isfile(creds_path):
        with open(creds_path, encoding="utf-8") as f:
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
    print(
        "No AWS credentials found (AWS_PROFILE, AWS_ACCESS_KEY_ID/SECRET, or ~/.aws/credentials [default]).",
        file=sys.stderr,
    )
    print("Run without --non-interactive to be prompted, or export credentials first.", file=sys.stderr)
    sys.exit(1)


def detect_probable_aws_region():
    """Best-effort region from env, boto3 session, AWS CLI, or ~/.aws/config for the active profile."""
    for key in ("AWS_REGION", "AWS_DEFAULT_REGION"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val

    try:
        import boto3

        region = boto3.Session().region_name
        if region:
            return region
    except Exception:
        pass

    profile = (os.environ.get("AWS_PROFILE") or "").strip()
    cmd = ["aws", "configure", "get", "region"]
    if profile:
        cmd.extend(["--profile", profile])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        region = (result.stdout or "").strip()
        if result.returncode == 0 and region:
            return region
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    config_path = os.path.expanduser(os.path.join("~", ".aws", "config"))
    if os.path.isfile(config_path):
        section = f"profile {profile}" if profile else "default"
        try:
            with open(config_path, encoding="utf-8") as f:
                in_section = False
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("[") and stripped.endswith("]"):
                        in_section = stripped[1:-1].strip() == section
                        continue
                    if in_section and stripped.startswith("region"):
                        _, _, val = stripped.partition("=")
                        val = val.strip().strip('"').strip("'")
                        if val:
                            return val
        except OSError:
            pass

    return ""


def resolve_aws_region(cli_region, current):
    """Prefer explicit CLI, then an already-configured project region, then profile detection."""
    if (cli_region or "").strip():
        return cli_region.strip()

    cfg = (current.get("aws_region") or "").strip()
    bucket = (current.get("terraform_state_bucket") or "").strip()
    if cfg and bucket and bucket != constants.TERRAFORM_STATE_BUCKET_PLACEHOLDER:
        return cfg

    detected = detect_probable_aws_region()
    if detected:
        return detected
    return cfg or "us-west-2"
