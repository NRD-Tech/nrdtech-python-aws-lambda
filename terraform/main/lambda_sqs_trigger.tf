
# ######################################################
# # Triggering Lambda via an SQS Queue
# ######################################################

# resource "aws_sqs_queue" "lambda_trigger_queue" {
#   # Give this an name that reflects what kind of jobs it is queueing
#   # Note: be sure to leave the environment variable in the name so you
#   #       have different queues for staging and production
#   name = var.APP_IDENT

#   # Set this to the max length of time a lambda function could possibly run
#   visibility_timeout_seconds = var.APP_TIMEOUT

#   redrive_policy = jsonencode({
#     deadLetterTargetArn = aws_sqs_queue.dlq.arn

#     # Set this to an appropriate retry count for your application
#     maxReceiveCount = 3
#   })
# }

# # Dead Letter Queue (DLQ)
# resource "aws_sqs_queue" "dlq" {
#   name = "${var.APP_IDENT}-dlq"
# }

# resource "aws_lambda_event_source_mapping" "lambda_sqs_trigger" {
#   event_source_arn = aws_sqs_queue.lambda_trigger_queue.arn
#   function_name    = aws_lambda_function.lambda_function.function_name
#   enabled          = true  # Set to false to disable the trigger

#   batch_size = 10  # Number of messages that are sent to the lambda function at a time (min=1, max=10)
#   maximum_batching_window_in_seconds = 1  # Max amount of time, in seconds, to gather records before invoking the function (only works on Standard Queue's - not fifo)
# }

# resource "aws_iam_policy" "sqs_permissions_policy" {
#   name        = "${var.APP_IDENT}_sqs_permissions"
#   policy      = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Effect = "Allow",
#         Action = [
#           "sqs:ReceiveMessage",
#           "sqs:DeleteMessage",
#           "sqs:GetQueueAttributes"
#         ],
#         Resource = aws_sqs_queue.lambda_trigger_queue.arn
#       }
#     ]
#   })
# }

# resource "aws_iam_role_policy_attachment" "sqs_permissions_policy_attachment" {
#   role       = aws_iam_role.lambda_exec.name
#   policy_arn = aws_iam_policy.sqs_permissions_policy.arn
# }
