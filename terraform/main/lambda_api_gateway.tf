# API Gateway trigger - active when trigger_type = "api_gateway"
# Set API_DOMAIN and API_ROOT_DOMAIN in config.<env> when using this trigger.

locals {
  api_gateway_enabled = var.trigger_type == "api_gateway"
  api_stage_name      = var.ENVIRONMENT
}

resource "aws_api_gateway_rest_api" "api" {
  count = local.api_gateway_enabled ? 1 : 0

  name        = "${var.APP_IDENT}_api"
  description = "API for ${var.APP_IDENT} application"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "proxy" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api[0].id
  parent_id   = aws_api_gateway_rest_api.api[0].root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy_any" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.api[0].id
  resource_id   = aws_api_gateway_resource.proxy[0].id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_integration" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id             = aws_api_gateway_rest_api.api[0].id
  resource_id             = aws_api_gateway_resource.proxy[0].id
  http_method             = aws_api_gateway_method.proxy_any[0].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.lambda_function.invoke_arn
}

resource "aws_lambda_permission" "apigw" {
  count = local.api_gateway_enabled ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.api[0].id}/*/*/*"
}

resource "aws_api_gateway_method" "proxy_options" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.api[0].id
  resource_id   = aws_api_gateway_resource.proxy[0].id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method_response" "proxy_options_200" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api[0].id
  resource_id = aws_api_gateway_resource.proxy[0].id
  http_method = aws_api_gateway_method.proxy_options[0].http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration" "proxy_options" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api[0].id
  resource_id = aws_api_gateway_resource.proxy[0].id
  http_method = aws_api_gateway_method.proxy_options[0].http_method
  type        = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_integration_response" "proxy_options_200" {
  count = local.api_gateway_enabled ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api[0].id
  resource_id = aws_api_gateway_resource.proxy[0].id
  http_method = aws_api_gateway_method.proxy_options[0].http_method
  status_code = aws_api_gateway_method_response.proxy_options_200[0].status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'*'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_deployment" "deployment" {
  count = local.api_gateway_enabled ? 1 : 0

  depends_on = [
    aws_api_gateway_integration.proxy_integration,
    aws_api_gateway_method.proxy_options,
    aws_api_gateway_method_response.proxy_options_200,
    aws_api_gateway_integration_response.proxy_options_200
  ]

  rest_api_id = aws_api_gateway_rest_api.api[0].id
  variables   = { deployment = "1" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_log_group" "api_gateway_log_group" {
  count = local.api_gateway_enabled ? 1 : 0

  name              = "/aws/apigateway/${var.APP_IDENT}_api"
  retention_in_days  = 3
}

resource "aws_api_gateway_stage" "api_stage" {
  count = local.api_gateway_enabled ? 1 : 0

  stage_name    = local.api_stage_name
  rest_api_id   = aws_api_gateway_rest_api.api[0].id
  deployment_id = aws_api_gateway_deployment.deployment[0].id

  xray_tracing_enabled = true
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_log_group[0].arn
    format = jsonencode({
      request_id = "$context.requestId"
      ip         = "$context.identity.sourceIp"
      http_method = "$context.httpMethod"
      resource_path = "$context.resourcePath"
      status = "$context.status"
    })
  }
}

# Custom domain (optional - only created when API_DOMAIN / API_ROOT_DOMAIN are set)
data "aws_route53_zone" "api_domain" {
  count = local.api_gateway_enabled && var.API_ROOT_DOMAIN != "" ? 1 : 0

  name = "${var.API_ROOT_DOMAIN}."
}

resource "aws_acm_certificate" "cert" {
  count = local.api_gateway_enabled && var.API_DOMAIN != "" ? 1 : 0

  provider          = aws.useast1
  domain_name       = var.API_DOMAIN
  validation_method = "DNS"

  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cert_validation_records" {
  for_each = length(aws_acm_certificate.cert) > 0 ? {
    for dvo in aws_acm_certificate.cert[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  provider = aws.useast1
  zone_id  = data.aws_route53_zone.api_domain[0].zone_id
  name     = each.value.name
  type     = each.value.type
  records  = [each.value.record]
  ttl      = 60
}

resource "aws_acm_certificate_validation" "cert_validation" {
  count = local.api_gateway_enabled && var.API_DOMAIN != "" ? 1 : 0

  provider                = aws.useast1
  certificate_arn         = aws_acm_certificate.cert[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation_records : r.fqdn]
}

resource "aws_api_gateway_domain_name" "custom_domain" {
  count = local.api_gateway_enabled && var.API_DOMAIN != "" ? 1 : 0

  domain_name     = var.API_DOMAIN
  certificate_arn = aws_acm_certificate_validation.cert_validation[0].certificate_arn
}

resource "aws_api_gateway_base_path_mapping" "mapping" {
  count = local.api_gateway_enabled && var.API_DOMAIN != "" ? 1 : 0

  depends_on = [aws_api_gateway_deployment.deployment, aws_api_gateway_stage.api_stage]

  api_id      = aws_api_gateway_rest_api.api[0].id
  stage_name  = aws_api_gateway_stage.api_stage[0].stage_name
  domain_name = aws_api_gateway_domain_name.custom_domain[0].domain_name
}

resource "aws_route53_record" "api_gateway" {
  count = local.api_gateway_enabled && var.API_DOMAIN != "" && var.API_ROOT_DOMAIN != "" ? 1 : 0

  zone_id = data.aws_route53_zone.api_domain[0].zone_id
  name    = var.API_DOMAIN
  type    = "A"
  alias {
    name                   = aws_api_gateway_domain_name.custom_domain[0].cloudfront_domain_name
    zone_id                = aws_api_gateway_domain_name.custom_domain[0].cloudfront_zone_id
    evaluate_target_health = false
  }
}

resource "aws_iam_role" "api_gateway_cloudwatch_role" {
  count = local.api_gateway_enabled ? 1 : 0

  name = "${var.APP_IDENT}_api_gateway_cw_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "apigateway.amazonaws.com" }
    }]
  })
}

data "aws_iam_policy_document" "api_gateway_cloudwatch_policy" {
  count = local.api_gateway_enabled ? 1 : 0

  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogGroups", "logs:DescribeLogStreams", "logs:PutLogEvents", "logs:GetLogEvents", "logs:FilterLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "api_gateway_cloudwatch_policy" {
  count = local.api_gateway_enabled ? 1 : 0

  name   = "${var.APP_IDENT}_api_gateway_cw_policy"
  role   = aws_iam_role.api_gateway_cloudwatch_role[0].id
  policy = data.aws_iam_policy_document.api_gateway_cloudwatch_policy[0].json
}

resource "aws_api_gateway_account" "account" {
  count = local.api_gateway_enabled ? 1 : 0

  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role[0].arn
}
