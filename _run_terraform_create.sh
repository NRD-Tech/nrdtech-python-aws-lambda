# NOTE: Do not call this directly - it is called from ./deploy.sh
# Local convenience: plan + apply -auto-approve (no saved-plan gate).
# CI should use _run_terraform_plan.sh then _run_terraform_apply_plan.sh.

set -euo pipefail

#########################################################
# Generate the backend.tf file for main
#########################################################

cd terraform/main
rm -fR .terraform
rm -fR .terraform.lock.hcl
cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket = "${TERRAFORM_STATE_BUCKET}"
    key    = "terraform-${TERRAFORM_STATE_IDENT}.tfstate"
    region = "${AWS_DEFAULT_REGION}"
    use_lockfile = true
  }
}
EOF

#########################################################
# Run Terraform
#########################################################

terraform init

apply_log=$(mktemp)
trap 'rm -f "$apply_log"' EXIT
echo "Creating resources..."
terraform apply -auto-approve 2>&1 | tee "$apply_log"
apply_code=${PIPESTATUS[0]}

if [[ $apply_code -ne 0 ]] && grep -q "Error: Cycle" "$apply_log"; then
  echo "Cycle detected (switching trigger type). Running two-phase apply: first disable all triggers, then apply desired trigger."
  saved_trigger="${TF_VAR_trigger_type:-}"
  export TF_VAR_trigger_type=none
  terraform apply -auto-approve
  export TF_VAR_trigger_type="$saved_trigger"
  terraform apply -auto-approve
elif [[ $apply_code -ne 0 ]]; then
  exit $apply_code
fi
