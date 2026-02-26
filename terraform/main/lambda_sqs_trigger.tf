######################################################
# Triggering Lambda via an SQS Queue
# Active when trigger_type = "sqs"
######################################################

resource "aws_sqs_queue" "lambda_trigger_queue" {
  count = var.trigger_type == "sqs" ? 1 : 0

  name = var.APP_IDENT
  visibility_timeout_seconds = var.APP_TIMEOUT

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "dlq" {
  count = var.trigger_type == "sqs" ? 1 : 0

  name = "${var.APP_IDENT}-dlq"
}

resource "aws_lambda_event_source_mapping" "lambda_sqs_trigger" {
  count = var.trigger_type == "sqs" ? 1 : 0

  event_source_arn  = aws_sqs_queue.lambda_trigger_queue[0].arn
  function_name     = aws_lambda_function.lambda_function.function_name
  enabled           = true
  batch_size        = 10
  maximum_batching_window_in_seconds = 1
}

resource "aws_iam_policy" "sqs_permissions_policy" {
  count = var.trigger_type == "sqs" ? 1 : 0

  name   = "${var.APP_IDENT}_sqs_permissions"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.lambda_trigger_queue[0].arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sqs_permissions_policy_attachment" {
  count = var.trigger_type == "sqs" ? 1 : 0

  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.sqs_permissions_policy[0].arn
}
