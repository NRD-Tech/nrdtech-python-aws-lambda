# NOTE: Do not call this directly - it is called from ./deploy.sh

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
  }
}
EOF

#########################################################
# Run Terraform
#########################################################

# Initialize terraform
terraform init

echo "Creating resources..."
apply_log=$(mktemp)
apply_code=0
terraform apply -auto-approve 2>&1 | tee "$apply_log" || apply_code=${PIPESTATUS[0]}

if [[ $apply_code -ne 0 ]] && grep -q "Error: Cycle" "$apply_log"; then
  echo "Cycle detected (switching trigger type). Running two-phase apply: first disable all triggers, then apply desired trigger."
  saved_trigger="${TF_VAR_trigger_type:-}"
  export TF_VAR_trigger_type=none
  terraform apply -auto-approve
  export TF_VAR_trigger_type="$saved_trigger"
  terraform apply -auto-approve
elif [[ $apply_code -ne 0 ]]; then
  rm -f "$apply_log"
  exit $apply_code
fi
rm -f "$apply_log"
