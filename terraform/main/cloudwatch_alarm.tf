resource "aws_sns_topic" "sns_topic" {
  name = "${var.app_ident}-alerts"
}

# Add a CloudWatch alarm for Lambda function failures
resource "aws_cloudwatch_metric_alarm" "failure_metric_alarm" {
  count = var.environment == "prod" ? 1 : 0
  alarm_name          = "${var.app_ident}-failure-alarm"
  alarm_description   = "Alarm when ${var.app_ident} encounters any failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1  # Trigger after 1 evaluation period
  datapoints_to_alarm = 1  # Alarm if at least 1 failure is detected
  threshold           = 0  # Threshold for failures is >0
  alarm_actions       = [aws_sns_topic.sns_topic.arn]
  treat_missing_data  = "notBreaching"

  metric_query {
    id = "e1"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 60  # 1-minute granularity
      stat        = "Sum"
      dimensions = {
        FunctionName = aws_lambda_function.lambda_function.function_name
      }
    }
    return_data = true
  }
}
