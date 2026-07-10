#!/bin/bash

set -e

####################################################################################################
# Check if Docker is running
####################################################################################################
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Please start Docker and try again."
  exit 1
fi

####################################################################################################
# Determine Flags / Action
#   ENVIRONMENT=staging ./deploy.sh           # local full apply (auto-approve)
#   ENVIRONMENT=staging ./deploy.sh plan      # plan only (writes terraform/main/tfplan)
#   ENVIRONMENT=staging ./deploy.sh apply     # apply saved plan from ./deploy.sh plan
#   ENVIRONMENT=staging ./deploy.sh destroy   # destroy (-d also works)
####################################################################################################
FLAG_DESTROY=false
ACTION="full"
while getopts "d" opt; do
  case ${opt} in
  d)
    FLAG_DESTROY=true
    ;;
  \?)
    echo "Invalid option: -$OPTARG" 1>&2
    exit 1
    ;;
  esac
done
shift $((OPTIND - 1))

case "${1:-}" in
  plan) ACTION="plan" ;;
  apply) ACTION="apply" ;;
  destroy) FLAG_DESTROY=true ;;
  "") ;;
  *)
    echo "Unknown action: $1 (expected plan|apply|destroy)" 1>&2
    exit 1
    ;;
esac

####################################################################################################
# Determine Environment
####################################################################################################
if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "prod" ]]; then
  echo "Invalid environment: ${ENVIRONMENT}. Allowed values are 'staging', or 'prod'."
  exit 1
fi

echo "ENVIRONMENT: ${ENVIRONMENT}"
echo "FLAG_DESTROY: ${FLAG_DESTROY}"
echo "ACTION: ${ACTION}"

#########################################################
# Configure Environment
#########################################################

# CI (Bitbucket OIDC): write web-identity token when present
if [[ -n "${BITBUCKET_STEP_OIDC_TOKEN:-}" ]]; then
  echo "$BITBUCKET_STEP_OIDC_TOKEN" > "$(pwd)/web-identity-token"
fi

# shellcheck source=/dev/null
source config.global
# shellcheck source=/dev/null
source "config.${ENVIRONMENT}"

# Ensure Terraform and AWS SDKs see a region
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-west-2}"
export AWS_REGION="${AWS_REGION:-$AWS_DEFAULT_REGION}"

# Local deploys use AWS_PROFILE / access keys — don't force web-identity
if [[ -z "${BITBUCKET_STEP_OIDC_TOKEN:-}" && -z "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]]; then
  unset AWS_WEB_IDENTITY_TOKEN_FILE
fi

# Default PROJECT_NAME to repository name when unset
export PROJECT_NAME="${PROJECT_NAME:-$APP_IDENT_WITHOUT_ENV}"

#########################################################
# Export all environment variables to Terraform
#########################################################
echo "Exporting all environment variables to Terraform..."

# Use process substitution to avoid subshell
while IFS= read -r line; do
  [[ "$line" == *=* ]] || continue
  var_name="${line%%=*}"
  var_value="${line#*=}"
  # Skip variables that already have TF_VAR_ prefix
  if [[ "$var_name" != TF_VAR_* ]]; then
    export "TF_VAR_${var_name}"="${var_value}"
    escaped_value="${var_value//\'/\'\\\'\'}"
    echo "Exported TF_VAR_${var_name}='${escaped_value}'"  # Debug log
  else
    echo "Skipped ${var_name} (already has TF_VAR_ prefix)"  # Debug log
  fi
done < <(printenv)

####################################################################################################
# Run Terraform
####################################################################################################
chmod +x ./*.sh 2>/dev/null || true

if [ "$FLAG_DESTROY" = true ] ; then
    bash ./_run_terraform_destroy.sh
elif [ "$ACTION" = "plan" ]; then
    bash ./_run_terraform_plan.sh
elif [ "$ACTION" = "apply" ]; then
    bash ./_run_terraform_apply_plan.sh
else
    bash ./_run_terraform_create.sh
fi
