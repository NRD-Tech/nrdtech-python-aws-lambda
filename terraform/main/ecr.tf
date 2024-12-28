resource "aws_ecr_repository" "ecr_repository" {
  name = "${var.app_ident}_repository"
  image_tag_mutability = "MUTABLE"
  force_delete = true
}

resource "aws_ecr_lifecycle_policy" "lifecycle_policy" {
  repository = aws_ecr_repository.ecr_repository.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection    = {
          tagStatus = "any"
          countType = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
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
  name = "${aws_ecr_repository.ecr_repository.repository_url}"
  build {
    context = "../../."
    tag = [
      "${aws_ecr_repository.ecr_repository.repository_url}:latest",
      "${aws_ecr_repository.ecr_repository.repository_url}:${filemd5(var.code_hash_file)}"
    ]
    cache_from = [
      "${aws_ecr_repository.ecr_repository.repository_url}:latest"
    ]
  }
  triggers = {
    code_hash = filemd5(var.code_hash_file)
  }
  platform = "linux/x86_64"
}

# push image to ecr repo
resource "docker_registry_image" "hash_image" {
  depends_on = [docker_image.terraform_function_image]
  name = "${aws_ecr_repository.ecr_repository.repository_url}:${filemd5(var.code_hash_file)}"
  triggers = {
    code_hash = filemd5(var.code_hash_file)
  }
  keep_remotely = true
}

resource "docker_registry_image" "latest_image" {
  depends_on = [docker_image.terraform_function_image]
  name = "${aws_ecr_repository.ecr_repository.repository_url}:latest"
  triggers = {
    code_hash = filemd5(var.code_hash_file)
  }
  keep_remotely = true
}
