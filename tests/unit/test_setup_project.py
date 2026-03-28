"""Unit tests for setup.py (project setup script)."""
import importlib.util
import os
import sys
import tempfile

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SPEC = importlib.util.spec_from_file_location(
    "setup_project",
    os.path.join(_PROJECT_ROOT, "setup.py"),
)
setup_project = importlib.util.module_from_spec(_SPEC)
sys.modules["setup_project"] = setup_project
_SPEC.loader.exec_module(setup_project)


# ---------------------------------------------------------------------------
# _parse_export_file
# ---------------------------------------------------------------------------
def test_parse_export_file_missing_returns_empty():
    assert setup_project._parse_export_file("/nonexistent/path") == {}


def test_parse_export_file_parses_export_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write('export FOO=bar\n')
        f.write('export BAR="baz"\n')
        f.write("export QUX='quux'\n")
        f.write("# export SKIP=no\n")
        f.write("not export BAD=line\n")
        path = f.name
    try:
        out = setup_project._parse_export_file(path)
        assert out["FOO"] == "bar"
        assert out["BAR"] == "baz"
        assert out["QUX"] == "quux"
        assert "SKIP" not in out
        assert "BAD" not in out
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Terraform helpers
# ---------------------------------------------------------------------------
def test_looks_like_terraform_code_resource():
    assert setup_project._looks_like_terraform_code('resource "aws_lambda_function" "x" {') is True


def test_looks_like_terraform_code_data():
    assert setup_project._looks_like_terraform_code('data "aws_region" "current" {}') is True


def test_looks_like_terraform_code_assignment():
    assert setup_project._looks_like_terraform_code("  name = var.APP_IDENT") is True


def test_looks_like_terraform_code_empty():
    assert setup_project._looks_like_terraform_code("") is True


# ---------------------------------------------------------------------------
# Constants consistency
# ---------------------------------------------------------------------------
def test_app_types_and_tf_files_consistent():
    assert set(setup_project.APP_TYPES) == set(setup_project.TF_FILE_BY_TYPE.keys())
    assert set(setup_project.APP_TYPES) == set(setup_project.HANDLER_FILE_BY_TYPE.keys())


def test_app_types_and_trigger_map_consistent():
    assert set(setup_project.APP_TYPES) == set(setup_project.TRIGGER_TYPE_MAP.keys())


def test_lambda_app_types():
    assert setup_project.APP_TYPES == ("api", "sqs_triggered", "scheduled")


# ---------------------------------------------------------------------------
# Placeholder checks
# ---------------------------------------------------------------------------
def test_is_placeholder_bucket():
    assert setup_project._is_placeholder_bucket("mycompany-terraform-state") is True
    assert setup_project._is_placeholder_bucket("") is True
    assert setup_project._is_placeholder_bucket("real-bucket") is False


def test_is_placeholder_role():
    assert setup_project._is_placeholder_role("arn:aws:iam::1234567890:role/test") is True
    assert setup_project._is_placeholder_role("") is True
    assert setup_project._is_placeholder_role("arn:aws:iam::999999999999:role/real") is False


# ---------------------------------------------------------------------------
# CLI --help
# ---------------------------------------------------------------------------
def test_main_help_exits_zero():
    orig = sys.argv
    try:
        sys.argv = ["setup.py", "--help"]
        with pytest.raises(SystemExit) as exc_info:
            setup_project.main()
        assert exc_info.value.code == 0
    finally:
        sys.argv = orig


# ---------------------------------------------------------------------------
# --non-interactive without required args
# ---------------------------------------------------------------------------
def test_main_non_interactive_missing_required(capsys, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    orig = sys.argv
    try:
        sys.argv = ["setup.py", "--non-interactive"]
        result = setup_project.main()
        assert result == 1
        err = capsys.readouterr().err.lower()
        assert "required" in err or "app-type" in err
    finally:
        sys.argv = orig


# ---------------------------------------------------------------------------
# Full non-interactive run writes config files
# ---------------------------------------------------------------------------
def test_non_interactive_full_run_writes_configs(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

    # Create terraform dir with tf files and handler templates
    tf_dir = tmp_path / "terraform" / "main"
    tf_dir.mkdir(parents=True)
    for tf_name in setup_project.TF_FILE_BY_TYPE.values():
        (tf_dir / tf_name).write_text("# resource \"aws_lambda_function\" \"fn\" {\n# }\n")

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    for handler_name in setup_project.HANDLER_FILE_BY_TYPE.values():
        (app_dir / handler_name).write_text("def handler(event, context): pass\n")

    monkeypatch.setattr(setup_project, "SCRIPT_DIR", str(tmp_path))
    monkeypatch.setattr(setup_project, "TERRAFORM_MAIN", str(tf_dir))
    monkeypatch.setattr(setup_project, "APP_DIR", str(app_dir))
    monkeypatch.setattr(setup_project, "CONFIG_GLOBAL", str(tmp_path / "config.global"))
    monkeypatch.setattr(setup_project, "CONFIG_STAGING", str(tmp_path / "config.staging"))
    monkeypatch.setattr(setup_project, "CONFIG_PROD", str(tmp_path / "config.prod"))

    orig = sys.argv
    try:
        sys.argv = [
            "setup.py", "--non-interactive",
            "--app-type", "api",
            "--app-name", "test-app",
            "--terraform-state-bucket", "my-bucket",
            "--aws-role-arn", "arn:aws:iam::999:role/test",
        ]
        result = setup_project.main()
        assert result == 0
    finally:
        sys.argv = orig

    assert (tmp_path / "config.global").exists()
    assert (tmp_path / "config.staging").exists()
    assert (tmp_path / "config.prod").exists()

    global_text = (tmp_path / "config.global").read_text()
    assert "test-app" in global_text
    assert "my-bucket" in global_text

    staging_text = (tmp_path / "config.staging").read_text()
    assert "API_ROOT_DOMAIN" in staging_text

    # Verify handler was copied
    assert (app_dir / "lambda_handler.py").exists()


def test_non_interactive_sqs_triggered_type(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

    tf_dir = tmp_path / "terraform" / "main"
    tf_dir.mkdir(parents=True)
    for tf_name in setup_project.TF_FILE_BY_TYPE.values():
        (tf_dir / tf_name).write_text("# resource \"aws_lambda_function\" \"fn\" {\n# }\n")

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    for handler_name in setup_project.HANDLER_FILE_BY_TYPE.values():
        (app_dir / handler_name).write_text("def handler(event, context): pass\n")

    monkeypatch.setattr(setup_project, "SCRIPT_DIR", str(tmp_path))
    monkeypatch.setattr(setup_project, "TERRAFORM_MAIN", str(tf_dir))
    monkeypatch.setattr(setup_project, "APP_DIR", str(app_dir))
    monkeypatch.setattr(setup_project, "CONFIG_GLOBAL", str(tmp_path / "config.global"))
    monkeypatch.setattr(setup_project, "CONFIG_STAGING", str(tmp_path / "config.staging"))
    monkeypatch.setattr(setup_project, "CONFIG_PROD", str(tmp_path / "config.prod"))

    orig = sys.argv
    try:
        sys.argv = [
            "setup.py", "--non-interactive",
            "--app-type", "sqs_triggered",
            "--app-name", "queue-worker",
            "--terraform-state-bucket", "my-bucket",
            "--aws-role-arn", "arn:aws:iam::999:role/test",
        ]
        result = setup_project.main()
        assert result == 0
    finally:
        sys.argv = orig

    # SQS type should have placeholder API domain in staging
    staging_text = (tmp_path / "config.staging").read_text()
    assert "example.com" in staging_text
