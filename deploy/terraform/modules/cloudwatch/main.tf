# CloudWatch Monitoring Module for ClawShell

# Log Groups
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = 30

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "alb" {
  name              = "/aws/alb/${var.name_prefix}"
  retention_in_days = 30

  tags = var.tags
}

# Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # ECS CPU Utilization
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "ECS CPU Utilization"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ECS",
              "CPUUtilization",
              "ServiceName", var.ecs_service_name,
              "ClusterName", var.ecs_cluster_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
        }
      },
      # ECS Memory Utilization
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "ECS Memory Utilization"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ECS",
              "MemoryUtilization",
              "ServiceName", var.ecs_service_name,
              "ClusterName", var.ecs_cluster_name
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
        }
      },
      # Request Count
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "Request Count"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ApplicationELB",
              "RequestCount",
              "LoadBalancer", var.alb_name_suffix
            ]
          ]
          period = 60
          stat   = "Sum"
          region = var.aws_region
        }
      },
      # Target Response Time
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "Target Response Time (ms)"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ApplicationELB",
              "TargetResponseTime",
              "LoadBalancer", var.alb_name_suffix
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
        }
      },
      # 5XX Errors
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "5XX Errors"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ApplicationELB",
              "HTTPCode_Target_5XX_Count",
              "LoadBalancer", var.alb_name_suffix
            ]
          ]
          period = 60
          stat   = "Sum"
          region = var.aws_region
        }
      },
      # Healthy Host Count
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "Healthy Host Count"
          view  = "timeSeries"
          stacked = false
          metrics = [
            [
              "AWS/ApplicationELB",
              "HealthyHostCount",
              "TargetGroup", var.target_group_name,
              "LoadBalancer", var.alb_name_suffix
            ]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
        }
      }
    ]
  })
}

# Alarms

# High CPU Alarm
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${var.name_prefix}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS CPU utilization is above 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = var.ecs_service_name
    ClusterName = var.ecs_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# High Memory Alarm
resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "${var.name_prefix}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS Memory utilization is above 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = var.ecs_service_name
    ClusterName = var.ecs_cluster_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# High Response Time Alarm
resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "${var.name_prefix}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 2  # 2 seconds
  alarm_description   = "Average response time is above 2 seconds"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_name_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# 5XX Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "high_5xx" {
  alarm_name          = "${var.name_prefix}-high-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "More than 10 5XX errors per minute"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_name_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# Low Healthy Hosts Alarm
resource "aws_cloudwatch_metric_alarm" "low_healthy_hosts" {
  alarm_name          = "${var.name_prefix}-low-healthy-hosts"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "No healthy hosts available"
  treat_missing_data  = "breaching"

  dimensions = {
    TargetGroup  = var.target_group_name
    LoadBalancer = var.alb_name_suffix
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.tags
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-alerts"
  tags = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Variables
variable "name_prefix" { type = string }
variable "ecs_cluster_name" { type = string }
variable "ecs_service_name" { type = string }
variable "alb_name_suffix" { type = string }
variable "target_group_name" { type = string }
variable "aws_region" { type = string }
variable "alert_email" { type = string }
variable "tags" { type = map(string) }

# Outputs
output "dashboard_url" {
  value = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
