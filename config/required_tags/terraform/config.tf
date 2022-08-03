
# enable config recorder
resource "aws_config_configuration_recorder" "default" {
  name     = "default_config_recorder"
  role_arn = aws_iam_role.config_recorder.arn
}

resource "aws_iam_role" "config_recorder" {
  name = "awsconfig-default"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "config.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
POLICY
}

resource "aws_config_delivery_channel" "channel" {
  count          = module.this.enabled ? 1 : 0
  name           = module.aws_config_label.id
  s3_bucket_name = var.s3_bucket_id
  s3_key_prefix  = var.s3_key_prefix
  sns_topic_arn  = local.findings_notification_arn

  depends_on = [
    aws_config_configuration_recorder.recorder,
    module.iam_role,
  ]
}

resource "aws_config_configuration_recorder_status" "recorder_status" {
  count      = module.this.enabled ? 1 : 0
  name       = aws_config_configuration_recorder.recorder[0].name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.channel]
}

resource "aws_config_config_rule" "example" {
  name = "required_tags_all"

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.example.arn
  }

  input_parameters = length(each.value.input_parameters) > 0 ? jsonencode(each.value.input_parameters) : null
  tags             = merge(module.this.tags, each.value.tags)

  depends_on = [
    aws_config_configuration_recorder.default,
    aws_lambda_permission.config,
  ]
}
