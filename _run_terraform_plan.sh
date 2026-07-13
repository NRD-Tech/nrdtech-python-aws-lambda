# NOTE: Do not call this directly - it is called from ./deploy.sh
# Writes terraform/main/tfplan and terraform/main/tfplan.txt (human-readable).

set -euo pipefail

cd terraform/main
rm -fR .terraform
rm -fR .terraform.lock.hcl
rm -f tfplan tfplan.txt

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

terraform init
echo "Planning resources..."
terraform plan -out=tfplan -input=false
terraform show -no-color tfplan > tfplan.txt
echo "Plan written to terraform/main/tfplan (binary) and terraform/main/tfplan.txt"
