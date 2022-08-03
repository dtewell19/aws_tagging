from urllib import response
import boto3
import logging
from botocore.exceptions import ClientError


def add_default_tag(required_tags, incorrect_value, tag_not_present, configuration_item, credentials):
    arn = configuration_item['ARN']
    tag_list = {}

    tag = boto3.client(
        'resourcegroupstaggingapi',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

    remediated_tags = incorrect_value + tag_not_present
    for mtag in remediated_tags:
        for rtag, rvalues in required_tags.items():
            rvaluesplit = rvalues.split(",")
            missing_value = rvaluesplit[0]
            if mtag == rtag:
                required_tags.pop(rtag)
                tag_list[rtag] = missing_value
                break

    logging.info("Remediating tags: " + str(tag_list))

    response = tag.tag_resources(
        ResourceARNList=[arn],
        Tags=tag_list
    )
    logging.debug(response)

    return
