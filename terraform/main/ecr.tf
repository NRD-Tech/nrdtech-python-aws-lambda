resource "aws_ecr_repository" "ecr_repository" {
  name = "${var.app_ident}_repository"
  image_tag_mutability = "MUTABLE"
  force_delete = true
}

# get authorization credentials to push to ecr - this is equivalent to using aws cli to get password and logging in manually
data "aws_ecr_authorization_token" "token" {}

# configure docker provider
provider "docker" {
  registry_auth {
      address = data.aws_ecr_authorization_token.token.proxy_endpoint
      username = data.aws_ecr_authorization_token.token.user_name
      password  = data.aws_ecr_authorization_token.token.password
    }
}

# build docker image
resource "docker_image" "terraform_function_image" {
  name = "${aws_ecr_repository.ecr_repository.repository_url}:latest"
  build {
    context = "../../."
  }
  triggers = {
    code_hash = filemd5(var.code_hash_file)
  }
  platform = "linux/x86_64"
}

# push image to ecr repo
resource "docker_registry_image" "browser" {
  name = docker_image.terraform_function_image.name
}
