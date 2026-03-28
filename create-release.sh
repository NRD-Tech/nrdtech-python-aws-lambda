#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_NAME="create-release"

usage() {
  echo "Usage: $SCRIPT_NAME"
  echo "  Requires: gh (GitHub CLI), authenticated and in a git repo with a GitHub remote."
  exit 0
}

check_gh() {
  if ! command -v gh &>/dev/null; then
    echo "" >&2
    echo "gh (GitHub CLI) is not installed or not on your PATH." >&2
    echo "" >&2
    echo "Install it, then run this script again:" >&2
    echo "  • Mac (Homebrew):  brew install gh" >&2
    echo "  • Windows (winget): winget install GitHub.cli" >&2
    echo "  • Other:           https://cli.github.com/" >&2
    echo "" >&2
    exit 1
  fi
  if ! gh auth status &>/dev/null; then
    echo "" >&2
    echo "gh is not logged in or not set up for this repo." >&2
    echo "" >&2
    echo "Fix it by running:  gh auth login" >&2
    echo "  Then choose GitHub.com, HTTPS, and authenticate (browser or token)." >&2
    echo "" >&2
    exit 1
  fi
}

get_latest_release_tag() {
  local raw
  raw=$(gh release list --limit 1 --json tagName -q '.[0].tagName' 2>/dev/null) || true
  if [[ -z "${raw:-}" || "$raw" == "null" ]]; then
    echo ""
  else
    echo "$raw"
  fi
}

parse_semver() {
  local tag="$1"
  tag="${tag#v}"
  local major minor patch
  major="${tag%%.*}"
  minor="${tag#*.}"
  minor="${minor%%.*}"
  patch="${tag##*.}"
  if [[ ! "$major" =~ ^[0-9]+$ ]] || [[ ! "$minor" =~ ^[0-9]+$ ]] || [[ ! "$patch" =~ ^[0-9]+$ ]]; then
    echo "0 0 0"
    return
  fi
  echo "$major $minor $patch"
}

bump_version() {
  local major="$1" minor="$2" patch="$3" bump="$4"
  case "$bump" in
    major) echo "$((major + 1)) 0 0" ;;
    minor) echo "$major $((minor + 1)) 0" ;;
    patch) echo "$major $minor $((patch + 1))" ;;
    *) echo "0 0 0" ;;
  esac
}

next_version_for_bump() {
  local major="$1" minor="$2" patch="$3" bump="$4"
  local nm nj np
  read -r nm nj np < <(bump_version "$major" "$minor" "$patch" "$bump")
  echo "v${nm}.${nj}.${np}"
}

prompt_bump_type() {
  local major="$1" minor="$2" patch="$3" choice
  local v_major v_minor v_patch
  v_major=$(next_version_for_bump "$major" "$minor" "$patch" "major")
  v_minor=$(next_version_for_bump "$major" "$minor" "$patch" "minor")
  v_patch=$(next_version_for_bump "$major" "$minor" "$patch" "patch")
  while true; do
    echo "" >&2
    echo "Next version:" >&2
    echo "  1) major  → $v_major" >&2
    echo "  2) minor  → $v_minor" >&2
    echo "  3) patch  → $v_patch" >&2
    read -r -p "Choice [1-3]: " choice
    case "$choice" in
      1) echo "major"; return ;;
      2) echo "minor"; return ;;
      3) echo "patch"; return ;;
      *) echo "Enter 1, 2, or 3." >&2 ;;
    esac
  done
}

prompt_description() {
  local desc
  read -r -p "Short description for title: " desc
  echo "$desc"
}

prompt_confirm() {
  local confirm
  read -r -p "Type 'yes' to create the release: " confirm
  [[ "$confirm" == "yes" ]]
}

run_release() {
  local version="$1" title="$2"
  gh release create "v${version}" --title "$title" --generate-notes
}

main() {
  if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    usage
  fi

  check_gh

  local latest_tag
  latest_tag=$(get_latest_release_tag)
  if [[ -z "$latest_tag" ]]; then
    latest_tag="v0.0.0"
    echo "No existing releases found. Starting from $latest_tag"
  else
    echo "Latest release: $latest_tag"
  fi

  local major minor patch
  read -r major minor patch < <(parse_semver "$latest_tag")

  local bump_type
  bump_type=$(prompt_bump_type "$major" "$minor" "$patch")

  local new_major new_minor new_patch
  read -r new_major new_minor new_patch < <(bump_version "$major" "$minor" "$patch" "$bump_type")
  local new_version="${new_major}.${new_minor}.${new_patch}"

  local description
  description=$(prompt_description)
  if [[ -z "$description" ]]; then
    echo "Error: description cannot be empty." >&2
    exit 1
  fi

  local title="v${new_version} - ${description}"

  echo ""
  echo "--- Summary ---"
  echo "  Tag:    v${new_version}"
  echo "  Title:  ${title}"
  echo "  Notes:  --generate-notes (from commits/PRs)"
  echo ""

  if ! prompt_confirm; then
    echo "Aborted."
    exit 0
  fi

  run_release "$new_version" "$title"
  echo "Release v${new_version} created."
}

main "$@"
