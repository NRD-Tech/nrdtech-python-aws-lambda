"""Constants and paths for project setup."""

import os

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(_PACKAGE_DIR)

CONFIG_GLOBAL = os.path.join(SCRIPT_DIR, "config.global")


CONFIG_STAGING = os.path.join(SCRIPT_DIR, "config.staging")


CONFIG_PROD = os.path.join(SCRIPT_DIR, "config.prod")


GITHUB_WORKFLOWS = os.path.join(SCRIPT_DIR, ".github", "workflows")


WORKFLOW_DISABLED = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml.disabled")


WORKFLOW_ENABLED = os.path.join(GITHUB_WORKFLOWS, "github_flow.yml")


TERRAFORM_MAIN = os.path.join(SCRIPT_DIR, "terraform", "main")


APP_DIR = os.path.join(SCRIPT_DIR, "app")


APPROVAL_MODES = ("dispatch", "environment")


DEFAULT_APPROVAL_MODE = "dispatch"


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

OIDC_FEDERATION = "token.actions.githubusercontent.com"


TERRAFORM_STATE_BUCKET_PLACEHOLDER = "mycompany-terraform-state"


AWS_ROLE_ARN_PLACEHOLDER_ACCOUNT = "1234567890"


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
