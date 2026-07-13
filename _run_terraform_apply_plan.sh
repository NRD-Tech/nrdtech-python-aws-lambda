# NOTE: Do not call this directly - it is called from ./deploy.sh
# Applies terraform/main/tfplan produced by _run_terraform_plan.sh.
# Re-inits providers; the saved plan must match this configuration.

set -euo pipefail

cd terraform/main

if [[ ! -f tfplan ]]; then
  echo "No saved plan at terraform/main/tfplan. Run: ENVIRONMENT=${ENVIRONMENT:-staging} ./deploy.sh plan" >&2
  exit 1
fi

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

# Keep existing .terraform if present (CI restores lockfile + plan artifact).
if [[ ! -d .terraform ]]; then
  terraform init
fi

echo "Applying saved plan..."
terraform apply -input=false tfplan
rm -f tfplan tfplan.txt
