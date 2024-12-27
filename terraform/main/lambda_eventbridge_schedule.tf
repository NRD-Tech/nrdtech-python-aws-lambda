
# ######################################################
# # Triggering Lambda via an EventBridge Schedule
# ######################################################
# resource "aws_scheduler_schedule" "scheduled-lambda-execution" {
#   name = "${var.app_ident}-schedule"

#   flexible_time_window {
#     mode = "OFF"
#   }

#   # Cron Style Scheduling
#   schedule_expression = var.environment == "prod" ? "cron(0 */3 * * ? *)" : "cron(0 */12 * * ? *)"

#   # Rate Style Scheduling
#   # schedule_expression = var.environment == "prod" ? "rate(3 hour)" : "rate(12 hour)"

#   target {
#     arn      = aws_lambda_function.lambda_function.arn
#     role_arn = aws_iam_role.eventbridge_schedule_role.arn
#     input = "{}"
#   }
# }

# resource "aws_iam_role" "eventbridge_schedule_role" {
#   name = "${var.app_ident}-EBScheduleRole"
#   assume_role_policy = <<EOF
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Action": "sts:AssumeRole",
#       "Principal": {
#         "Service": "scheduler.amazonaws.com"
#       },
#       "Effect": "Allow",
#       "Sid": ""
#     }
#   ]
# }
# EOF
# }

# resource "aws_iam_role_policy" "eventbridge_schedule_policy" {
#   name = "${var.app_ident}-EBScheduledLambdaPolicy"
#   role = aws_iam_role.eventbridge_schedule_role.id

#   policy = <<EOF
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Action": [
#         "lambda:InvokeFunction"
#       ],
#       "Effect": "Allow",
#       "Resource": "*"
#     }
#   ]
# }
# EOF
# }
