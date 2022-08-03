#!/usr/bin/env python3
import os

import aws_cdk as cdk

from config_tag_remediation.config_tag_remediation_stack import ConfigTagRemediationStack
from config_tag_remediation.config_tag_remediation_stack import ConfigTagRuleStack


app = cdk.App()
remediation_stack = ConfigTagRemediationStack(
    app,
    "ConfigTagRemediationStack"
)

rule_stack = ConfigTagRuleStack(
    app,
    "ConfigTagRuleStack",
    lambda_function=remediation_stack.lambda_function,
    admin_role=remediation_stack.config_remediation_role
)

app.synth()
