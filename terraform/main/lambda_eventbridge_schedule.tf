
# ######################################################
# # Triggering Lambda via an EventBridge Schedule
# ######################################################
# resource "aws_scheduler_schedule" "scheduled-lambda-execution" {
#   # Must be no longer than 64 characters
#   name = "${var.APP_IDENT}-schedule"

#   flexible_time_window {
#     mode = "OFF"
#   }

#   # NOTE: All environments except prod are disabled by default here
#   state = var.ENVIRONMENT == "prod" ? "ENABLED" : "DISABLED"

#   # Cron Style Scheduling
#   schedule_expression = var.ENVIRONMENT == "prod" ? "cron(0 */3 * * ? *)" : "cron(0 */12 * * ? *)"

#   # Rate Style Scheduling
#   # schedule_expression = var.ENVIRONMENT == "prod" ? "rate(3 hour)" : "rate(12 hour)"

#   target {
#     arn      = aws_lambda_function.lambda_function.arn
#     role_arn = aws_iam_role.eventbridge_schedule_role.arn
#     input = "{}"
#   }
# }

# resource "aws_iam_role" "eventbridge_schedule_role" {
#   name = "${var.APP_IDENT}-EBScheduleRole"
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
#   name = "${var.APP_IDENT}-EBScheduledLambdaPolicy"
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
