data "aws_sns_topic" "sns_topic" {
  name = var.sns_topic_name
}

# Add a CloudWatch alarm for Lambda function that fails to run at an expected frequency
resource "aws_cloudwatch_metric_alarm" "success_metric_alarm" {
  count = var.environment == "prod" ? 1 : 0
  alarm_name          = "${var.app_ident}-success-metric-alarm"
  alarm_description   = "Alarm when ${var.app_ident} does not achieve 100% success"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = var.alarm_after_n_minutes_without_success  # Alarm after N evaluation periods
  datapoints_to_alarm = var.alarm_after_n_minutes_without_success  # Alarm only if all periods indicate a problem
  threshold           = 100  # Threshold for success rate (100%)
  alarm_actions       = [data.aws_sns_topic.sns_topic.arn]
  treat_missing_data  = "breaching"

  metric_query {
    id = "e1"
    expression = "100 - (errors / invocations) * 100"
    label = "Success Rate (%)"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      metric_name = "Errors"
      namespace   = "AWS/Lambda"
      period      = 60  # 1-minute granularity
      stat        = "Sum"
      dimensions = {
        FunctionName = aws_lambda_function.lambda_function.function_name
      }
    }
  }

  metric_query {
    id = "invocations"
    metric {
      metric_name = "Invocations"
      namespace   = "AWS/Lambda"
      period      = 60  # 1-minute granularity
      stat        = "Sum"
      dimensions = {
        FunctionName = aws_lambda_function.lambda_function.function_name
      }
    }
  }
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
  alarm_actions       = [data.aws_sns_topic.sns_topic.arn]
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
