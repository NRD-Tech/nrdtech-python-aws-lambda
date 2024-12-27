# For Custom VPC
# resource "aws_security_group" "lambda_sg" {
#   name   = "${var.app_ident}_lambda_sg"
#   vpc_id = data.aws_vpc.selected.id

#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

resource "aws_lambda_function" "lambda_function" {
  depends_on = [docker_registry_image.hash_image]
  function_name = var.app_ident
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri = "${aws_ecr_repository.ecr_repository.repository_url}:${docker_image.terraform_function_image.triggers.code_hash}"
  timeout = var.app_timeout
  memory_size = var.app_memory

  # For Custom VPC
  # Note: Use the vpc setting here if you need access to private resources like RDS
  #       instances but note that accessing general internet resources will not work
  #       unless your VPC has a NAT setup.
  # vpc_config {
  #   subnet_ids         = data.aws_subnet_ids.private.ids
  #   security_group_ids = [aws_security_group.lambda_sg.id]
  # }

  environment {
    variables = {
      ENVIRONMENT = var.environment,
      APP_IDENT = var.app_ident
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.app_ident}_lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com",
        },
        Effect = "Allow",
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.app_ident}_Policy"
  policy      = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "cloudwatch:PutMetricData"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "cloudwatch_put_metric_policy_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}
