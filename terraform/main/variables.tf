variable "AWS_REGION" {
  type = string
}

variable "APP_IDENT" {
  description = "Identifier of the application"
  type        = string
}

variable "APP_IDENT_WITHOUT_ENV" {
    description = "Identifier of the application that doesn't include the environment"
    type = string
}

variable "ENVIRONMENT" {
  type        = string
}

variable "CODE_HASH_FILE" {
  description = "Filename of the code hash file"
  type        = string
}

variable "APP_TIMEOUT" {
  description = "Number of seconds until the lambda function times out"
  type        = number
}

variable "APP_MEMORY" {
  description = "Number of megabytes of memory to allocate to the lambda function"
  type        = number
}

variable "CPU_ARCHITECTURE" {
  description = "X86_64 or ARM64"
  type = string
}

##################################################
# Trigger type: one of api_gateway, sqs, eventbridge
# Switching triggers uses a two-phase apply to avoid cycles.
##################################################
variable "trigger_type" {
  description = "Lambda trigger: api_gateway, sqs, or eventbridge. Set in config.global / config.<env>. Use 'none' only for internal two-phase apply."
  type        = string
  default     = "sqs"
}

##################################################
# API Gateway variables (only when trigger_type = api_gateway)
##################################################
variable "API_DOMAIN" {
  type    = string
  default = ""
}

variable "API_ROOT_DOMAIN" {
  type    = string
  default = ""
}

##################################################
# Code Artifact
##################################################
variable "CODEARTIFACT_TOKEN" {
  description = "CodeArtifact token for authentication"
  type        = string
  default = ""
}
