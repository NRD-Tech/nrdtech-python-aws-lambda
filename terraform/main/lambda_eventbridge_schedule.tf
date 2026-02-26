######################################################
# Triggering Lambda via an EventBridge Schedule
# Active when trigger_type = "eventbridge"
######################################################

resource "aws_scheduler_schedule" "scheduled_lambda_execution" {
  count = var.trigger_type == "eventbridge" ? 1 : 0

  name = "${var.APP_IDENT}-schedule"

  flexible_time_window {
    mode = "OFF"
  }

  state = var.ENVIRONMENT == "prod" ? "ENABLED" : "DISABLED"
  schedule_expression = var.ENVIRONMENT == "prod" ? "cron(0 */3 * * ? *)" : "cron(0 */12 * * ? *)"

  target {
    arn     = aws_lambda_function.lambda_function.arn
    role_arn = aws_iam_role.eventbridge_schedule_role[0].arn
    input   = "{}"
  }
}

resource "aws_iam_role" "eventbridge_schedule_role" {
  count = var.trigger_type == "eventbridge" ? 1 : 0

  name = "${var.APP_IDENT}-EBScheduleRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "sts:AssumeRole"
        Principal = { Service = "scheduler.amazonaws.com" }
        Effect   = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_schedule_policy" {
  count = var.trigger_type == "eventbridge" ? 1 : 0

  name   = "${var.APP_IDENT}-EBScheduledLambdaPolicy"
  role   = aws_iam_role.eventbridge_schedule_role[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["lambda:InvokeFunction"]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
