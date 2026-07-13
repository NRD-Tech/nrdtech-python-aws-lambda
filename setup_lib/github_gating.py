"""GitHub CLI gating, approval mode, and protections."""

import json
import os
import re
import shutil
import subprocess
import sys

from setup_lib import constants
from setup_lib.prompts import prompt, prompt_yes_no


def find_gh_executable():
    """Locate gh on macOS/Linux/Windows without assuming PATH is perfect."""
    found = shutil.which("gh")
    if found:
        return found
    candidates = []
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        candidates.extend(
            [
                os.path.join(pf, "GitHub CLI", "gh.exe"),
                os.path.join(pf86, "GitHub CLI", "gh.exe"),
                os.path.join(local, "Programs", "GitHub CLI", "gh.exe"),
            ]
        )
    else:
        candidates.extend(
            [
                "/opt/homebrew/bin/gh",
                "/usr/local/bin/gh",
                os.path.expanduser("~/.local/bin/gh"),
            ]
        )
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return ""


def run_gh(gh, args, timeout=60):
    """Run gh; return (ok, stdout, stderr). Never raises for missing auth."""
    cmd = [gh] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, (result.stdout or "").strip(), (result.stderr or "").strip()
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, "", str(exc)


def parse_gh_auth_accounts(status_text):
    """Parse `gh auth status` into [{'login': ..., 'active': bool}, ...]."""
    accounts = []
    current = None
    for line in (status_text or "").splitlines():
        m = re.search(r"Logged in to github\.com account (\S+)", line)
        if m:
            current = {"login": m.group(1).strip(), "active": False}
            accounts.append(current)
            continue
        if current and "Active account: true" in line:
            current["active"] = True
    return accounts


def git_remote_github_owner_repo():
    """Best-effort owner/repo from git remote origin (https or ssh)."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=constants.SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return "", ""
    url = (result.stdout or "").strip()
    if not url:
        return "", ""
    m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$", url)
    if not m:
        return "", ""
    return m.group("owner"), m.group("repo")


def detect_github_org_plan(gh, org):
    """Return 'enterprise', 'team', or '' if unknown / inaccessible."""
    if not gh or not org:
        return ""
    ok, out, _ = run_gh(gh, ["api", f"orgs/{org}", "--jq", ".plan.name"])
    if not ok or not out:
        return ""
    name = out.strip().lower()
    if name in ("enterprise", "business"):
        return "enterprise"
    if name in ("team", "pro", "free"):
        return "team"
    return ""


def approval_mode_for_plan(plan_name):
    if plan_name == "enterprise":
        return "environment"
    return constants.DEFAULT_APPROVAL_MODE


def ensure_gh_ready_for_org(gh, org, non_interactive):
    """
    Ensure gh works and the active account can see org.
    Handles missing gh, wrong account, and prints switch instructions (incl. Windows).
    Returns (ok, active_login, messages).
    """
    messages = []
    if not gh:
        messages.append(
            "GitHub CLI (gh) not found. Install from https://cli.github.com/ "
            "(macOS: brew install gh | Windows: winget install GitHub.cli), then re-run setup."
        )
        return False, "", messages

    ok, out, err = run_gh(gh, ["auth", "status"])
    status_text = "\n".join(x for x in (out, err) if x)
    accounts = parse_gh_auth_accounts(status_text)
    if not accounts:
        messages.append(
            "gh is installed but not logged in. Run: gh auth login\n"
            "Then re-run setup (or set --github-approval-mode manually)."
        )
        return False, "", messages

    active = next((a["login"] for a in accounts if a.get("active")), accounts[0]["login"])
    if not org:
        return True, active, messages

    ok, _, err = run_gh(gh, ["api", f"orgs/{org}/memberships/{active}"])
    if ok:
        return True, active, messages

    # Wrong account or no access — try other logged-in accounts
    for acct in accounts:
        login = acct["login"]
        if login == active:
            continue
        ok_sw, _, err_sw = run_gh(gh, ["auth", "switch", "--user", login])
        if not ok_sw:
            messages.append(f"Could not switch gh user to {login}: {err_sw}")
            continue
        ok_m, _, _ = run_gh(gh, ["api", f"orgs/{org}/memberships/{login}"])
        if ok_m:
            messages.append(f"Switched gh active account to {login} for org {org}.")
            return True, login, messages
        # switch back
        run_gh(gh, ["auth", "switch", "--user", active])

    other = [a["login"] for a in accounts if a["login"] != active]
    hint = (
        "Active gh user '{}' cannot access org '{}'.\n"
        "Fix with: gh auth switch --user <login>   (logged in: {})\n"
        "Or: gh auth login   then re-run setup.\n"
        "On Windows use the same commands in PowerShell or Git Bash."
    ).format(active, org, ", ".join(other) if other else "none other")
    messages.append(hint)
    if non_interactive:
        return False, active, messages
    if prompt_yes_no("Continue without GitHub API setup (manual instructions only)?", default_no=False):
        return False, active, messages
    return False, active, messages


def resolve_github_approval_settings(args, current, non_interactive):
    """
    Resolve github_org + github_approval_mode.
    Prefer CLI flags, then config, then gh org plan detection (enterprise→environment, else dispatch).
    """
    owner, _repo = git_remote_github_owner_repo()
    org = (getattr(args, "github_org", "") or current.get("github_org", "") or owner or "").strip()
    mode = (getattr(args, "github_approval_mode", "") or current.get("github_approval_mode", "") or "").strip()

    gh = find_gh_executable()
    plan = ""
    if org:
        ok, _login, msgs = ensure_gh_ready_for_org(gh, org, non_interactive)
        for m in msgs:
            print(m, file=sys.stderr)
        if ok:
            plan = detect_github_org_plan(gh, org)
            if plan:
                print(f"Detected GitHub org '{org}' plan: {plan}")

    if not mode:
        mode = approval_mode_for_plan(plan) if plan else constants.DEFAULT_APPROVAL_MODE

    if not non_interactive:
        org = prompt("GitHub org (for approval-mode detection / protections)", org)
        if org and org != (getattr(args, "github_org", "") or current.get("github_org", "") or owner or "").strip():
            ok, _login, msgs = ensure_gh_ready_for_org(gh, org, non_interactive)
            for m in msgs:
                print(m, file=sys.stderr)
            if ok:
                plan = detect_github_org_plan(gh, org)
                if plan and not getattr(args, "github_approval_mode", ""):
                    mode = approval_mode_for_plan(plan)
                    print(f"Detected GitHub org '{org}' plan: {plan} → approval mode {mode}")
        default_mode = mode if mode in constants.APPROVAL_MODES else constants.DEFAULT_APPROVAL_MODE
        mode = prompt(
            "GitHub approval mode (dispatch=Team-safe plan then manual apply; environment=Enterprise Environment reviewers)",
            default_mode,
        )

    if mode not in constants.APPROVAL_MODES:
        print(f"Unknown approval mode '{mode}'; using {constants.DEFAULT_APPROVAL_MODE}", file=sys.stderr)
        mode = constants.DEFAULT_APPROVAL_MODE

    args.github_org = org
    args.github_approval_mode = mode
    args._gh_path = gh
    args._gh_plan = plan
    return gh, org, mode, plan


def enable_github_workflow():
    if os.path.isfile(constants.WORKFLOW_ENABLED):
        print(f"GitHub workflow already enabled at {constants.WORKFLOW_ENABLED}")
        return True
    if not os.path.isfile(constants.WORKFLOW_DISABLED):
        print(f"Warning: {constants.WORKFLOW_DISABLED} not found", file=sys.stderr)
        return False
    os.rename(constants.WORKFLOW_DISABLED, constants.WORKFLOW_ENABLED)
    print(f"Enabled GitHub workflow: {constants.WORKFLOW_ENABLED}")
    return True


def configure_github_protections(gh, org, mode, non_interactive):
    """Create Environments + main branch ruleset when API allows; always print manual steps."""
    owner, repo = git_remote_github_owner_repo()
    if org:
        owner = org
    if not owner or not repo:
        print(
            "\nGitHub protections (manual):\n"
            "  1. Settings → Branches/Rules: require PR + 1 review before merge to main\n"
            "  2. Settings → Environments: create 'staging' and 'production'\n"
            "  3. On Enterprise: add required reviewers on those environments "
            "(staging=developers, production=team leads; prevent self-review on production)\n"
            "  4. Team (private): use GITHUB_APPROVAL_MODE=dispatch — merge plans on push; "
            "apply via Actions → Run workflow\n"
        )
        return

    print(f"\nConfiguring GitHub protections for {owner}/{repo} (mode={mode})...")
    if not gh:
        print("  Skipped API calls (gh not available). Use the manual steps below.")
    else:
        for env_name in ("staging", "production"):
            # Empty body — Team private repos reject wait_timer / required reviewers.
            try:
                result = subprocess.run(
                    [gh, "api", "-X", "PUT", f"repos/{owner}/{repo}/environments/{env_name}", "--input", "-"],
                    input="{}",
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    print(f"  Ensured environment '{env_name}'")
                else:
                    err = (result.stderr or result.stdout or "").strip()
                    print("  Could not create environment '{}': {}".format(env_name, err or "unknown error"))
            except (subprocess.TimeoutExpired, OSError) as exc:
                print(f"  Could not create environment '{env_name}': {exc}")

        if mode == "environment":
            print(
                "  Enterprise mode: in Settings → Environments, add required reviewers "
                "on 'staging' and 'production' (prevent self-review on production)."
            )

        # Branch ruleset: require PR + reviews on main (best-effort)
        ruleset = {
            "name": "main-protection",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
            "rules": [
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 1,
                        "dismiss_stale_reviews_on_push": True,
                        "require_code_owner_review": False,
                        "require_last_push_approval": False,
                        "required_review_thread_resolution": False,
                    },
                },
            ],
        }
        try:
            result = subprocess.run(
                [gh, "api", "-X", "POST", f"repos/{owner}/{repo}/rulesets", "--input", "-"],
                input=json.dumps(ruleset),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("  Created/ensured ruleset 'main-protection' (PR + 1 review)")
            else:
                err_text = (result.stderr or result.stdout or "").strip()
                if "already exists" in err_text.lower() or "Name must be unique" in err_text:
                    print("  Ruleset 'main-protection' already exists")
                else:
                    print(f"  Could not create ruleset (need admin): {err_text[:300]}")
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"  Could not create ruleset: {exc}")

    print(
        "\nManual checklist:\n"
        "  • Require PR reviews before merge to main (rulesets / branch protection)\n"
        "  • Review terraform plan in Actions (job summary) before apply\n"
        "  • dispatch mode: Actions → Run workflow → deploy after reviewing plan\n"
        "  • environment mode: approve the Environment gate on the apply job\n"
        "  • production: team-lead reviewers only\n"
    )
