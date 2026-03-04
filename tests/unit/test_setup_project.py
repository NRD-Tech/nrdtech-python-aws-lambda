"""Unit tests for setup.py (project setup script)."""
import importlib.util
import os
import sys
import tempfile

import pytest

# Load setup.py as a module to avoid setuptools conflict
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SPEC = importlib.util.spec_from_file_location(
    "setup_project",
    os.path.join(_PROJECT_ROOT, "setup.py"),
)
setup_project = importlib.util.module_from_spec(_SPEC)
sys.modules["setup_project"] = setup_project
_SPEC.loader.exec_module(setup_project)


def test_parse_export_file_missing_returns_empty():
    assert setup_project._parse_export_file("/nonexistent/path") == {}


def test_parse_export_file_parses_export_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write('export FOO=bar\n')
        f.write('export BAR="baz"\n')
        f.write('export QUX=\'quux\'\n')
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


def test_looks_like_terraform_code_resource():
    assert setup_project._looks_like_terraform_code("resource \"aws_lambda_function\" \"x\" {") is True


def test_looks_like_terraform_code_data():
    assert setup_project._looks_like_terraform_code("data \"aws_region\" \"current\" {}") is True


def test_looks_like_terraform_code_assignment():
    assert setup_project._looks_like_terraform_code("  name = var.APP_IDENT") is True


def test_looks_like_terraform_code_comment():
    assert setup_project._looks_like_terraform_code("# this is a comment") is False


def test_looks_like_terraform_code_empty():
    assert setup_project._looks_like_terraform_code("") is True


def test_main_help_exits_zero():
    orig_argv = sys.argv
    try:
        sys.argv = ["setup.py", "--help"]
        with pytest.raises(SystemExit) as exc_info:
            setup_project.main()
        assert exc_info.value.code == 0
    finally:
        sys.argv = orig_argv


def test_main_non_interactive_missing_required_exits_one(capsys):
    orig_argv = sys.argv
    try:
        sys.argv = ["setup.py", "--non-interactive"]
        result = setup_project.main()
        assert result == 1
        err = capsys.readouterr().err.lower()
        assert "required" in err or "app-type" in err
    finally:
        sys.argv = orig_argv


def test_app_types_and_tf_files_consistent():
    assert set(setup_project.APP_TYPES) == set(setup_project.TF_FILE_BY_TYPE.keys())
    assert set(setup_project.APP_TYPES) == set(setup_project.HANDLER_FILE_BY_TYPE.keys())
