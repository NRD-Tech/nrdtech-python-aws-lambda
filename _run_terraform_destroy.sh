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

cat > app_bootstrap.tf << EOF
data "terraform_remote_state" "app_bootstrap" {
  backend = "s3"
  config = {
    bucket = "${TERRAFORM_STATE_BUCKET}"
    key    = "terraform-app-${TERRAFORM_STATE_IDENT}.tfstate"
    region = "${AWS_DEFAULT_REGION}"
  }
}
EOF

#########################################################
# Generate the remote_backend.tf file for access
# to the shared infrastructure elements
#########################################################

#cat > remote_backend.tf << EOF
# data "terraform_remote_state" "core" {
#   backend = "s3"
#   config = {
#     bucket = "${TERRAFORM_STATE_BUCKET}"
#     key    = "terraform.tfstate"
#     region = "${AWS_DEFAULT_REGION}"
#   }
# }
#EOF

#########################################################
# Run Terraform
#########################################################

# Initialize terraform
terraform init

echo "Destroying resources..."
terraform destroy -auto-approve

cd ../../

#########################################################
# Generate the backend.tf file for app_bootstrap
#########################################################

cd terraform/bootstrap
rm -fR .terraform
rm -fR .terraform.lock.hcl
cat > backend.tf << EOF
terraform {
  backend "s3" {
    bucket = "${TERRAFORM_STATE_BUCKET}"
    key    = "terraform-app-${TERRAFORM_STATE_IDENT}.tfstate"
    region = "${AWS_DEFAULT_REGION}"
  }
}
EOF

#########################################################
# Run App Bootstrap Terraform
#########################################################

# Initialize terraform
terraform init
echo "Destroying resources..."
terraform destroy -auto-approve
