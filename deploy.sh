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
# Determine Flags
####################################################################################################
while getopts "d" opt; do
  case ${opt} in
  d)
    export FLAG_DESTROY=true
    ;;
  \?)
    echo "Invalid option: -$OPTARG" 1>&2
    exit 1
    ;;
  esac
done
shift $((OPTIND - 1))

####################################################################################################
# Determine Environment
####################################################################################################
# If the provided environment is not one of the allowed values, exit the script
if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "prod" ]]; then
  echo "Invalid environment: ${ENVIRONMENT}. Allowed values are 'staging', or 'prod'."
  exit 1
fi

echo "ENVIRONMENT: ${ENVIRONMENT}"
echo "FLAG_DESTROY: ${FLAG_DESTROY}"

#########################################################
# Configure Environment
#########################################################

echo $BITBUCKET_STEP_OIDC_TOKEN > $(pwd)/web-identity-token

source config.global
source "config.${ENVIRONMENT}"

#########################################################
# Export all environment variables to Terraform
#########################################################
echo "Exporting all environment variables to Terraform..."

# Use process substitution to avoid subshell
while IFS='=' read -r var_name var_value; do
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
if [ "$FLAG_DESTROY" = true ] ; then
    bash ./_run_terraform_destroy.sh
else
    bash ./_run_terraform_create.sh
fi
