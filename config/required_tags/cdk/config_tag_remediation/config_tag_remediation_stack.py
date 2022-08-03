from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_config as config,
    Stack, App, Duration
)


class ConfigTagRemediationStack(Stack):
    def __init__(self, app: App, id: str) -> None:
        super().__init__(app, id)

        self.config_remediation_role = iam.Role(
            self, 'config_tag_remediation_role',
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name='configRemediationLambdaRole',
            description='IAM Role for use by Lambda for Config detection and remediation'
        )

        self.config_remediation_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))
        self.config_remediation_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSConfigRole"))
        self.config_remediation_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            "ResourceGroupsandTagEditorFullAccess"))
        self.config_remediation_role.attach_inline_policy(iam.Policy(self, "crossaccount-policy",
                                                                     statements=[iam.PolicyStatement(
                                                                         actions=[
                                                                             "sts:AssumeRole"],
                                                                         resources=[
                                                                             'arn:aws:iam::*:role/configRemediationLambdaRole'],
                                                                         conditions={
                                                                             "ForAnyValue:StringLike": {
                                                                                 "aws:PrincipalOrgID": "o-123456789"
                                                                             }
                                                                         }
                                                                     )]
                                                                     ))

        lambda_code_bucket = s3.Bucket.from_bucket_attributes(
            self, 'config_tag_remediation_s3',
            bucket_name='config-tag-remediation'
        )

        self.lambda_function = lambda_.Function(
            self, 'config_tag_remediation_lambda',
            function_name='config_tag_remediation',
            description='Custom Lambda for use with AWS Config to determine required tag conpliance and automating redemiation.',
            code=lambda_.S3Code(
                bucket=lambda_code_bucket,
                key='lambda.zip'
            ),
            handler='handler.lambda_handler',
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(900),
            role=self.config_remediation_role
        )


class ConfigTagRuleStack(Stack):
    def __init__(self, app: App, id: str, lambda_function, admin_role, **kwargs) -> None:
        super().__init__(app, id, **kwargs)

        config_tag_rule = config.CustomRule(
            self, 'config_tag_remediation_rule',
            config_rule_name='required_tag_remediation',
            description='Custom Config Rule for determining required tag conpliance and automating redemiation.',
            configuration_changes=True,
            lambda_function=lambda_function,
            input_parameters={
                "Key1": "Value1"
            },
            rule_scope=config.RuleScope.from_resource(
                config.ResourceType.EC2_INSTANCE)
        )

        config_remediation_role = iam.Role(
            self, 'config_tag_remediation_role',
            assumed_by=iam.OrganizationPrincipal("o-h6ucntxo9v"),
            role_name='configRemediationLambdaRole',
            description='IAM Role for use by Lambda for Config detection and remediation'
        )

        config_remediation_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSConfigRole"))
        config_remediation_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(
            "ResourceGroupsandTagEditorFullAccess"))
        config_remediation_role.add_to_policy(iam.PolicyStatement(
            actions=["ec2:CreateTags", "ec2:DeleteTags"],
            resources=["*"]
        )
        )
