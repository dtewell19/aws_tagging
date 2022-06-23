#
# This file made available under CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/legalcode)
#
# Ensure that resources have required tags, and that tags have valid values.
#
# Trigger Type: Change Triggered
# Scope of Changes: EC2:Instance
# Accepted Parameters: requiredTagKey1, requiredTagValues1, requiredTagKey2, ...
# Example Values: 'CostCenter', 'R&D,Ops', 'Environment', 'Stage,Dev,Prod', ...
#                 An asterisk '*' as the value will just check that any value is set for that key


import json
import boto3
import logging
from botocore.exceptions import ClientError
from remediation import remediate_tag
from notification import send_violation_email, send_remediation_email

logging.basicConfig(level=logging.INFO)

# Specify desired resource types to validate
APPLICABLE_RESOURCES = ["AWS::EC2::Instance"]


# Iterate through required tags ensureing each required tag is present,
# and value is one of the given valid values
def find_violation(current_tags, required_tags, configuration_item):
    logging.warn("Resource Id: " + configuration_item['resourceId'])
    logging.warn("Required Tags: " + str(required_tags))
    logging.warn("Current Tags: " + str(current_tags))

    violation = ""
    for rtag, rvalues in required_tags.items():
        tag_present = False

        for key, value in current_tags.items():
            if key == rtag:
                value_match = False
                tag_present = True
                rvaluesplit = rvalues.split(",")
                for rvalue in rvaluesplit:
                    if value == rvalue:
                        value_match = True
                    if value != "":
                        if rvalue == "*":
                            value_match = True
                if value_match is not True:
                    violation = violation + "\n Value \'" + value + \
                        "\' doesn't match any of " + required_tags[rtag] + "!"

        if not tag_present:
            violation = violation + "\n" + "Tag " + \
                str(rtag) + " is not present."

    if violation == "":
        logging.warn("No violation found.")
        return None

    else:
        logging.warn(violation)
        # send_violation_email(configuration_item, current_tags, violation)
        logging.warn("Violation is being remediated.")
        remediate_tag(current_tags, required_tags, configuration_item)

        return violation


def evaluate_compliance(configuration_item, rule_parameters):
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The rule doesn't apply to resources of type " +
            configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    current_tags = configuration_item.get('tags')
    violation = find_violation(
        current_tags, rule_parameters, configuration_item)

    if violation:
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": violation
        }

    return {
        "compliance_type": "COMPLIANT",
        "annotation": "This resource is compliant with the rule."
    }


def lambda_handler(event, context):
    print(event)
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])

    result_token = "No token found."
    if "resultToken" in event:
        result_token = event["resultToken"]

    evaluation = evaluate_compliance(configuration_item, rule_parameters)
    logging.info(evaluation["compliance_type"] +
                 ": " + evaluation["annotation"])

    config = boto3.client("config")
    config.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType":
                    configuration_item["resourceType"],
                "ComplianceResourceId":
                    configuration_item["resourceId"],
                "ComplianceType":
                    evaluation["compliance_type"],
                "Annotation":
                    evaluation["annotation"],
                "OrderingTimestamp":
                    configuration_item["configurationItemCaptureTime"]
            },
        ],
        ResultToken=result_token
    )
