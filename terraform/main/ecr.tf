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

locals {
  docker_command = var.cpu_architecture == "ARM64" ? "docker buildx build --platform linux/arm64  --provenance=false" : "docker build"
}

resource "null_resource" "push_image" {
  triggers = {
    code_hash = filemd5(var.code_hash_file)
    ecr_repo = aws_ecr_repository.ecr_repository.repository_url
    force = 1
  }

  # NOTE: Modify the docker build command below to specify either x86_64 or ARM64
  #       * Bitbucket pipelines only supports x86_64
  #       * GitHub supports both
  provisioner "local-exec" {
    command = <<EOF
    set -e # Exit immediately if a command exits with a non-zero status.
    cd ../..

    echo "Running docker build: ${path.cwd}"

    echo "Log into AWS ECR Container Repository"
    aws ecr get-login-password \
      --region ${data.aws_region.current.name} | \
      docker login \
        --username AWS \
        --password-stdin ${aws_ecr_repository.ecr_repository.repository_url}

    # ARM64 (GitHub Only): docker buildx build --platform linux/arm64 \
    # x86_64 (BitBucket): docker build \
    # x86_64 (GitHub): docker buildx build --platform linux/amd64 \
    echo "Build the Docker Image"
    ${local.docker_command} \
      --no-cache \
      --push \
      --build-arg CODEARTIFACT_TOKEN="${var.codeartifact_token}" \
      -t ${aws_ecr_repository.ecr_repository.repository_url}:${self.triggers.code_hash} \
      -t ${aws_ecr_repository.ecr_repository.repository_url}:latest \
      .

    sleep 10
    EOF
  }
}
