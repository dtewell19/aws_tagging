module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"

  publish        = true
  create_package = true

  function_name = "config_required_tags"
  handler       = "index.handler"
  runtime       = "python3.9"
  source_path   = "${path.module}/../lambda/"

  # TO-DO: this access should be reduced
  policies                      = ["arn:aws:iam::aws:policy/AWSLambdaExecute", "arn:aws:iam::aws:policy/AmazonEC2FullAccess", "arn:aws:iam::aws:policy/AWSConfigRole", "arn:aws:iam::aws:policy/ResourceGroupsandTagEditorFullAccess", "arn:aws:iam::aws:policy/AmazonSESFullAccess"]
  attach_cloudwatch_logs_policy = false
}
