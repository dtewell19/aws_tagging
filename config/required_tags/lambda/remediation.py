import boto3
import logging
from botocore.exceptions import ClientError
from grpc import Status
from notification import send_violation_email, send_remediation_email


def remediate_tag(current_tags, required_tags, configuration_item):
    violation = ""
    status = ""
    arn = configuration_item['ARN']

    tag = boto3.client('resourcegroupstaggingapi')

    for rtag, rvalues in required_tags.items():
        tag_present = False
        rvaluesplit = rvalues.split(",")
        missing_value = rvaluesplit[0]

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
                    violation = violation + "Value \'" + value + \
                        "\' doesn't match any of " + \
                        required_tags[rtag] + "! \n"

        # add tag if its missing
        if not tag_present:
            violation = violation + "Tag " + \
                str(rtag) + " is not present. \n"
            status = "Adding tag " + rtag + " with value " + missing_value
            logging.info(status)
            response = tag.tag_resources(
                ResourceARNList=[arn],
                Tags={rtag: missing_value}
            )
            send_remediation_email(arn, current_tags, status)
            logging.warn(response)
    return status
