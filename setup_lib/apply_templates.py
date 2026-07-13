"""Apply project-specific source/Dockerfile/handler templates."""

import os
import shutil

from setup_lib import constants


def _looks_like_terraform_code(line):
    rest = line.strip()
    if not rest or rest in ("{", "}"):
        return True
    tf_prefixes = (
        "resource ",
        "data ",
        "output ",
        "variable ",
        "module ",
        "template ",
        "locals ",
        "aws_api_gateway",
        "aws_sqs",
        "aws_lambda",
        "aws_scheduler",
        "aws_iam",
        "aws_cloudwatch",
        "aws_ecr",
        "aws_route53",
        "aws_acm",
        "name ",
        "image ",
        "region ",
        "uri ",
        "arn ",
        "value ",
        "policy ",
        "role ",
        "statement ",
        "action ",
        "effect ",
        "principal ",
        "schedule_expression ",
        "target ",
        "flexible_time_window ",
        "state ",
        "batch_size ",
        "event_source_arn ",
        "function_name ",
        "enabled ",
        "environment ",
        "variables ",
        "rest_api_id ",
        "resource_id ",
        "http_method ",
        "integration_http_method ",
        "depends_on ",
        "endpoint_configuration ",
        "types ",
        "parent_id ",
        "path_part ",
        "authorization ",
        "type ",
        "integration ",
        "statement_id ",
        "source_arn ",
        "deployment_id ",
        "stage_name ",
        "domain_name ",
        "certificate_arn ",
        "zone_id ",
        "alias ",
        "response_parameters ",
        "request_templates ",
        "status_code ",
        "visibility_timeout_seconds ",
        "redrive_policy ",
        "maximum_batching_window ",
        "provisioner ",
        "triggers ",
        "policy_arn ",
        "assume_role_policy ",
        "countType ",
        "rulePriority ",
        "selection ",
        "countNumber ",
        "description ",
        "tags ",
    )
    if any(rest.startswith(p) for p in tf_prefixes):
        return True
    if rest.startswith("=") or " = " in rest:
        return True
    if line.startswith("# ") and len(line) > 2 and line[2] in " \t":
        return True
    return False


def uncomment_tf_file(path):
    with open(path, encoding="utf-8") as f:
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
    with open(path, encoding="utf-8") as f:
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
    path = os.path.join(constants.TERRAFORM_MAIN, tf_name)
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    has_active = any(line.strip().startswith(("resource ", "data ", "output ")) for line in lines if line.strip())
    if has_active:
        comment_tf_file(path)


def configure_terraform(app_type):
    """Trigger selection is via config trigger_type; all .tf files stay active with count gates."""
    trigger = constants.TRIGGER_TYPE_MAP.get(app_type, "eventbridge")
    print(f"Using trigger_type={trigger} (Terraform count gates; no .tf comment toggling)")


def configure_handler(app_type):
    src_name = constants.HANDLER_FILE_BY_TYPE[app_type]
    src = os.path.join(constants.APP_DIR, src_name)
    dst = os.path.join(constants.APP_DIR, "lambda_handler.py")
    if not os.path.isfile(src):
        print(f"Warning: {src_name} not found; skipping handler setup")
        return
    shutil.copy2(src, dst)
    print(f"Created app/lambda_handler.py from {src_name}")
