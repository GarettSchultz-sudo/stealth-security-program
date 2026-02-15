# CloudWatch Security Alarms for ClawShell

# Custom Metric Filters for Security Events
resource "aws_cloudwatch_log_metric_filter" "security_critical" {
  name           = "${var.name_prefix}-critical-security-events"
  log_group_name = var.log_group_name
  pattern        = "[timestamp, level=\"ERROR\", ...]", "severity=\"critical\""

  metric_transformation {
    name      = "CriticalSecurityEvents"
    namespace = "ClawShell/Security"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "security_blocked" {
  name           = "${var.name_prefix}-blocked-requests"
  log_group_name = var.log_group_name
  pattern        = "[timestamp, level=\"WARNING\", ...]", "action_taken=\"block\""

  metric_transformation {
    name      = "BlockedRequests"
    namespace = "ClawShell/Security"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "prompt_injection" {
  name           = "${var.name_prefix}-prompt-injection"
  log_group_name = var.log_group_name
  pattern        = "[timestamp, level=\"WARNING\", ...]", "threat_type=\"prompt_injection\""

  metric_transformation {
    name      = "PromptInjectionAttempts"
    namespace = "ClawShell/Security"
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "credential_exposure" {
  name           = "${var.name_prefix}-credential-exposure"
  log_group_name = var.log_group_name
  pattern        = "[timestamp, level=\"WARNING\", ...]", "threat_type=\"credential_exposure\""

  metric_transformation {
    name      = "CredentialExposureAttempts"
    namespace = "ClawShell/Security"
    value     = "1"
    unit      = "Count"
  }
}

# Security Alarms

# Critical Security Event Alarm
resource "aws_cloudwatch_metric_alarm" "critical_security" {
  alarm_name          = "${var.name_prefix}-critical-security"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CriticalSecurityEvents"
  namespace           = "ClawShell/Security"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Critical security event detected"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.sns_topic_arn]

  tags = var.tags
}

# High Blocked Request Rate Alarm
resource "aws_cloudwatch_metric_alarm" "high_blocked_rate" {
  alarm_name          = "${var.name_prefix}-high-blocked-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "BlockedRequests"
  namespace           = "ClawShell/Security"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "High rate of blocked requests (>10/minute)"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.sns_topic_arn]

  tags = var.tags
}

# Prompt Injection Surge Alarm
resource "aws_cloudwatch_metric_alarm" "prompt_injection_surge" {
  alarm_name          = "${var.name_prefix}-prompt-injection-surge"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "PromptInjectionAttempts"
  namespace           = "ClawShell/Security"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Surge in prompt injection attempts (>5/minute)"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.sns_topic_arn]

  tags = var.tags
}

# Credential Exposure Alarm
resource "aws_cloudwatch_metric_alarm" "credential_exposure" {
  alarm_name          = "${var.name_prefix}-credential-exposure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CredentialExposureAttempts"
  namespace           = "ClawShell/Security"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Credential exposure attempt detected"
  treat_missing_data  = "notBreaching"

  alarm_actions = [var.sns_topic_arn]

  tags = var.tags
}

# Composite Alarm for Attack Pattern
resource "aws_cloudwatch_composite_alarm" "attack_pattern" {
  alarm_name        = "${var.name_prefix}-attack-pattern"
  alarm_description = "Multiple security events indicate potential attack"

  alarm_rule = jsonencode({
    "Or" = [
      {
        "Alarm" = {
          "AlarmName" = aws_cloudwatch_metric_alarm.critical_security.alarm_name
          "Region"    = var.aws_region
        }
      },
      {
        "And" = [
          {
            "Alarm" = {
              "AlarmName" = aws_cloudwatch_metric_alarm.prompt_injection_surge.alarm_name
              "Region"    = var.aws_region
            }
          },
          {
            "Alarm" = {
              "AlarmName" = aws_cloudwatch_metric_alarm.credential_exposure.alarm_name
              "Region"    = var.aws_region
            }
          }
        ]
      }
    ]
  })

  actions_enabled = true
  alarm_actions   = [var.sns_topic_arn]

  tags = var.tags
}

# Variables
variable "log_group_name" { type = string }
variable "sns_topic_arn" { type = string }
variable "aws_region" { type = string }
variable "tags" { type = map(string) }
