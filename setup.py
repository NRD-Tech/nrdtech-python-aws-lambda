#!/usr/bin/env python3
"""
Setup for AWS Lambda (Python) template.
Configures app type (api | sqs_triggered | scheduled),
config.global / config.staging / config.prod, Terraform trigger files, and the active handler.
Auto-discovers OIDC role, Terraform state bucket, and Route53 domains.

Run from project root:  python3 setup.py [--app-type ...] [options]
Works on macOS and Windows (Python 3.6+). Safe to re-run.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import shutil  # noqa: F401 — kept so tests can monkeypatch setup_project.shutil

from setup_lib import github_gating  # noqa: F401
from setup_lib.apply_templates import _looks_like_terraform_code  # noqa: F401
from setup_lib.aws_creds import (  # noqa: F401
    detect_probable_aws_region,
    resolve_aws_region,
)
from setup_lib.cli import main  # noqa: F401
from setup_lib.config_io import _parse_export_file  # noqa: F401
from setup_lib.constants import (  # noqa: F401
    APP_DIR,
    APP_TYPES,
    CONFIG_GLOBAL,
    CONFIG_PROD,
    CONFIG_STAGING,
    HANDLER_FILE_BY_TYPE,
    SCRIPT_DIR,
    TERRAFORM_MAIN,
    TERRAFORM_STATE_BUCKET_PLACEHOLDER,
    TF_FILE_BY_TYPE,
    TRIGGER_TYPE_MAP,
    TRIGGER_TYPE_REVERSE,
)
from setup_lib.github_gating import (  # noqa: F401
    approval_mode_for_plan,
    parse_gh_auth_accounts,
)
from setup_lib.github_gating import (
    find_gh_executable as _find_gh_impl,
)
from setup_lib.prompts import (  # noqa: F401
    _is_placeholder_bucket,
    _is_placeholder_role,
)


def find_gh_executable():
    """Locate gh; honor monkeypatch of this module's shutil.which in unit tests."""
    orig_which = github_gating.shutil.which
    github_gating.shutil.which = shutil.which
    try:
        return _find_gh_impl()
    finally:
        github_gating.shutil.which = orig_which


if __name__ == "__main__":
    sys.exit(main())
