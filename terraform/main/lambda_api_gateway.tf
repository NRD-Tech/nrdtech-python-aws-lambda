# # 1. Create the API Gateway REST API

# resource "aws_api_gateway_rest_api" "api" {
#   name        = "${var.app_ident}_api"
#   description = "API for ${var.app_ident} application"
#   endpoint_configuration {
#     types = ["REGIONAL"]
#   }
# }

# # 2. Define a catch-all (proxy) resource for the API Gateway. This will forward all paths to the Lambda.

# resource "aws_api_gateway_resource" "proxy" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   parent_id   = aws_api_gateway_rest_api.api.root_resource_id
#   path_part   = "{proxy+}"
# }

# # 3. Allow any HTTP method on the catch-all resource.

# resource "aws_api_gateway_method" "proxy_any" {
#   rest_api_id   = aws_api_gateway_rest_api.api.id
#   resource_id   = aws_api_gateway_resource.proxy.id
#   http_method   = "ANY"
#   authorization = "NONE"
# }

# # 4. Set up the AWS Lambda proxy integration.

# resource "aws_api_gateway_integration" "proxy_integration" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   resource_id = aws_api_gateway_resource.proxy.id
#   http_method = aws_api_gateway_method.proxy_any.http_method

#   type                    = "AWS_PROXY"
#   integration_http_method = "POST"
#   uri                     = aws_lambda_function.lambda_function.invoke_arn
# }

# # 5. Grant API Gateway permissions to invoke the Lambda function.

# resource "aws_lambda_permission" "apigw" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.lambda_function.function_name
#   principal     = "apigateway.amazonaws.com"

#   source_arn = "arn:aws:execute-api:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.api.id}/*/*/*"
# }

# # 6. Deploy the API to an API Gateway stage, such as "v1".

# locals {
#   api_stage_name = var.environment
# }

# resource "aws_api_gateway_deployment" "deployment" {
#   depends_on = [
#     aws_api_gateway_integration.proxy_integration,
#     aws_api_gateway_method.proxy_options,
#     aws_api_gateway_method_response.proxy_options_200,
#     aws_api_gateway_integration_response.proxy_options_200
#   ]

#   rest_api_id = aws_api_gateway_rest_api.api.id

#   variables = {
#     deployment = "1"
#   }

#   lifecycle {
#     create_before_destroy = true
#   }
# }

# resource "aws_api_gateway_domain_name" "custom_domain" {
#   domain_name = var.api_domain
#   certificate_arn = aws_acm_certificate.cert.arn

#   depends_on = [aws_acm_certificate_validation.cert_validation]
# }

# resource "aws_acm_certificate" "cert" {
#   provider = aws.useast1
#   domain_name       = var.api_domain
#   validation_method = "DNS"

#   tags = {
#     Environment = "test"
#   }

#   lifecycle {
#     create_before_destroy = true
#   }
# }

# resource "aws_acm_certificate_validation" "cert_validation" {
#   provider = aws.useast1
#   certificate_arn         = aws_acm_certificate.cert.arn
#   validation_record_fqdns = [for record in aws_route53_record.cert_validation_records : record.fqdn]

#   depends_on = [aws_route53_record.cert_validation_records]
# }

# resource "aws_route53_record" "cert_validation_records" {
#   provider = aws.useast1
#   for_each = {
#     for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
#       name   = dvo.resource_record_name
#       record = dvo.resource_record_value
#       type   = dvo.resource_record_type
#     }
#   }

#   zone_id = data.aws_route53_zone.api_domain.zone_id
#   name    = each.value.name
#   type    = each.value.type
#   records = [each.value.record]
#   ttl     = 60
# }

# data "aws_route53_zone" "api_domain" {
#   name = "${var.api_root_domain}."
# }

# resource "aws_api_gateway_base_path_mapping" "mapping" {
#   depends_on = [aws_api_gateway_deployment.deployment, aws_api_gateway_stage.api_stage]

#   api_id      = aws_api_gateway_rest_api.api.id
#   stage_name  = local.api_stage_name
#   domain_name = aws_api_gateway_domain_name.custom_domain.domain_name
# }

# resource "aws_route53_record" "api_gateway" {
#   zone_id = data.aws_route53_zone.api_domain.zone_id
#   name    = var.api_domain
#   type    = "A"

#   alias {
#     name                   = aws_api_gateway_domain_name.custom_domain.cloudfront_domain_name
#     zone_id                = aws_api_gateway_domain_name.custom_domain.cloudfront_zone_id
#     evaluate_target_health = false
#   }
# }

# # The following is so the CORS works (still need to configure application to return CORS headers)

# resource "aws_api_gateway_method" "proxy_options" {
#   rest_api_id   = aws_api_gateway_rest_api.api.id
#   resource_id   = aws_api_gateway_resource.proxy.id
#   http_method   = "OPTIONS"
#   authorization = "NONE"
# }

# resource "aws_api_gateway_method_response" "proxy_options_200" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   resource_id = aws_api_gateway_resource.proxy.id
#   http_method = aws_api_gateway_method.proxy_options.http_method
#   status_code = "200"
#   response_parameters = {
#     "method.response.header.Access-Control-Allow-Headers" = true,
#     "method.response.header.Access-Control-Allow-Methods" = true,
#     "method.response.header.Access-Control-Allow-Origin"  = true
#   }
# }

# resource "aws_api_gateway_integration" "proxy_options" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   resource_id = aws_api_gateway_resource.proxy.id
#   http_method = aws_api_gateway_method.proxy_options.http_method
#   type        = "MOCK"

#   request_templates = {
#     "application/json" = "{\"statusCode\": 200}"
#   }
# }

# resource "aws_api_gateway_integration_response" "proxy_options_200" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   resource_id = aws_api_gateway_resource.proxy.id
#   http_method = aws_api_gateway_method.proxy_options.http_method
#   status_code = aws_api_gateway_method_response.proxy_options_200.status_code
#   response_parameters = {
#     "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
#     "method.response.header.Access-Control-Allow-Methods" = "'*'",
#     "method.response.header.Access-Control-Allow-Origin"  = "'*'"
#   }
# }

# ####################################################################################
# # Enable Logging on api gateway
# ####################################################################################

# resource "aws_cloudwatch_log_group" "api_gateway_log_group" {
#   name = "/aws/apigateway/${var.app_ident}_api"
#   retention_in_days = 3  # You can adjust this value as needed
# }

# resource "aws_api_gateway_stage" "api_stage" {
#   stage_name    = local.api_stage_name
#   rest_api_id   = aws_api_gateway_rest_api.api.id
#   deployment_id = aws_api_gateway_deployment.deployment.id

#   xray_tracing_enabled = true  # Optional, enables X-Ray tracing

#   # Logging settings
#   access_log_settings {
#     destination_arn = aws_cloudwatch_log_group.api_gateway_log_group.arn
#     format          = jsonencode({
#       request_id              = "$context.requestId",
#       ip                      = "$context.identity.sourceIp",
#       caller                  = "$context.identity.caller",
#       user                    = "$context.identity.user",
#       request_time            = "$context.requestTime",
#       http_method             = "$context.httpMethod",
#       resource_path           = "$context.resourcePath",
#       status                  = "$context.status",
#       protocol                = "$context.protocol",
#       integration_latency     = "$context.integrationLatency",
#       response_latency        = "$context.responseLatency",
#       api_id                  = "$context.apiId",
#       resource_id             = "$context.resourceId",
#       stage                   = "$context.stage",
#       request_time_epoch      = "$context.requestTimeEpoch",
#       request_parameters      = "$context.requestParameters",
#       response_payload_length = "$context.responsePayloadLength",
#       error_message           = "$context.errorMessage",
#       error_type              = "$context.errorType",
#       user_agent              = "$context.userAgent",
#       host                    = "$context.host"
#     })
#   }
# }

# resource "aws_iam_role" "api_gateway_cloudwatch_role" {
#   name = "${var.app_ident}_api_gateway_cw_role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Action = "sts:AssumeRole",
#         Effect = "Allow",
#         Principal = {
#           Service = "apigateway.amazonaws.com"
#         },
#       },
#     ],
#   })
# }

# resource "aws_iam_role_policy" "api_gateway_cloudwatch_policy" {
#   name   = "${var.app_ident}_api_gateway_cw_policy"
#   role   = aws_iam_role.api_gateway_cloudwatch_role.id
#   policy = data.aws_iam_policy_document.api_gateway_cloudwatch_policy.json
# }

# data "aws_iam_policy_document" "api_gateway_cloudwatch_policy" {
#   statement {
#     actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogGroups", "logs:DescribeLogStreams", "logs:PutLogEvents", "logs:GetLogEvents", "logs:FilterLogEvents"]
#     resources = ["arn:aws:logs:*:*:*"]
#   }
# }

# resource "aws_api_gateway_account" "account" {
#   cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_role.arn
# }
