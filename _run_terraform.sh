# NOTE: Do not call this directly - it is called indirectly from ./deploy_single_env.sh or ./deploy.sh

#########################################################
# Generate the backend.tf file
#########################################################

cd terraform
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

if [ "$FLAG_DESTROY" = true ] ; then
    echo "Destroying resources..."
    terraform destroy -auto-approve
else
    echo "Creating resources..."
    terraform apply -auto-approve
fi
