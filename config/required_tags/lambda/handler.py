# Ensure that resources have required tags, and that tags have valid values.
#
# Trigger Type: Change Triggered
# Scope of Changes: EC2:Instance, EC2::Volume
# Accepted Parameters: requiredTagKey1, requiredTagValues1, requiredTagKey2, ...
# Example Values: 'CostCenter', 'R&D,Ops', 'Environment', 'Stage,Dev,Prod', ...


import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from remediation import add_default_tag

logging.getLogger().setLevel(os.environ['LOG_LEVEL'])

# Specify desired resource types to validate
# full list of taggable resources: https://docs.aws.amazon.com/ARG/latest/userguide/supported-resources.html
# resource names follow cfn syntax: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html
APPLICABLE_RESOURCES = ["AWS::EC2::Instance", "AWS::EC2::Volume", "AWS::S3::Bucket", "AWS::DynamoDB::Table", "AWS::DynamoDB::GlobalTable", "AWS::RDS::DBCluster",
                        "AWS::RDS::DBInstance", "AWS::EFS::FileSystem", "AWS::FSx::FileSystem", "AWS::DocDB::DBCluster", "AWS::DocDB::DBInstance", "AWS::Neptune::DBCluster", "AWS::Neptune::DBInstance"]


# Iterate through required tags ensureing each required tag is present,
# and value is one of the given valid values
def find_violation(current_tags, required_tags, configuration_item, credentials):
    logging.info("Resource Id: " + configuration_item['resourceId'])
    logging.info("Required Tags: " + str(required_tags))
    logging.info("Current Tags: " + str(current_tags))

    incorrect_value = []
    case_mismatch = []
    tag_not_present = []

    for rtag, rvalues in required_tags.items():
        if rtag not in ['exec_role', 'Name']:
            tag_present = False
            value_match = False
            for key, value in current_tags.items():
                if key == rtag:
                    tag_present = True
                    rvaluesplit = rvalues.split(",")
                    for rvalue in rvaluesplit:
                        if value == rvalue:
                            value_match = True
                    if not value_match:
                        incorrect_value += rtag
                    break
                elif key.lower() == rtag.lower():
                    case_mismatch += rtag
                    break

            if tag_present and value_match:
                logging.info("No violation found for tag: " + rtag)
                current_tags.pop(rtag)
            else:
                tag_not_present += [rtag]
                logging.warn("Incorrect tag or value mismatch for " + rtag)

    if incorrect_value or tag_not_present:
        logging.warn("Remediating tags.")
        add_default_tag(required_tags, incorrect_value,
                        tag_not_present, configuration_item, credentials)

    return {
        "incorrect_value": incorrect_value,
        "tag_not_present": tag_not_present
    }


def evaluate_compliance(configuration_item, rule_parameters, credentials):
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
        current_tags, rule_parameters, configuration_item, credentials)

    if violation['incorrect_value'] or violation['tag_not_present']:
        return {
            "compliance_type": "NON_COMPLIANT",
            "annotation": "Required tags are not present or contain incorrect values. \n Missing tags: {} \n Incorrect Values: {}".format(str(violation['tag_not_present']), str(violation['incorrect_value'])),
            "incorrect_value": str(violation['incorrect_value']),
            "tag_not_present": str(violation['tag_not_present']),
        }
    else:
        return {
            "compliance_type": "COMPLIANT",
            "annotation": "This resource is compliant with the rule."
        }


def lambda_handler(event, context):
    logging.debug(event)
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])

    result_token = "No token found."
    if "resultToken" in event:
        result_token = event["resultToken"]

    sts_client = boto3.client('sts')

    assumed_role_object = sts_client.assume_role(
        RoleArn=rule_parameters['exec_role'],
        RoleSessionName="AsssumeCrossAccount"
    )

    credentials = assumed_role_object['Credentials']

    evaluation = evaluate_compliance(
        configuration_item, rule_parameters, credentials)
    logging.info(evaluation["compliance_type"] +
                 ": " + evaluation["annotation"])

    config = boto3.client(
        "config",
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )

    evaluation["annotation"] = (evaluation["annotation"][:250] + '..') if len(
        evaluation["annotation"]) > 250 else evaluation["annotation"]

    response = config.put_evaluations(
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
    logging.debug(response)


def main():
    event = {
        "version": "1.0",
        "invokingEvent": "{\"configurationItemDiff\":null,\"configurationItem\":{\"relatedEvents\":[],\"relationships\":[{\"resourceId\":\"eni-00ac815b08e1a96a4\",\"resourceName\":null,\"resourceType\":\"AWS::EC2::NetworkInterface\",\"name\":\"Contains NetworkInterface\"},{\"resourceId\":\"sg-0d992c24922ec4a34\",\"resourceName\":null,\"resourceType\":\"AWS::EC2::SecurityGroup\",\"name\":\"Is associated with SecurityGroup\"},{\"resourceId\":\"subnet-0e3fa4706db12eaee\",\"resourceName\":null,\"resourceType\":\"AWS::EC2::Subnet\",\"name\":\"Is contained in Subnet\"},{\"resourceId\":\"vol-0ed49bc4c16d69029\",\"resourceName\":null,\"resourceType\":\"AWS::EC2::Volume\",\"name\":\"Is attached to Volume\"},{\"resourceId\":\"vpc-07050ab479f8cc481\",\"resourceName\":null,\"resourceType\":\"AWS::EC2::VPC\",\"name\":\"Is contained in Vpc\"}],\"configuration\":{\"amiLaunchIndex\":0,\"imageId\":\"ami-0cff7528ff583bf9a\",\"instanceId\":\"i-06acc7778e56c246b\",\"instanceType\":\"t2.micro\",\"kernelId\":null,\"keyName\":null,\"launchTime\":\"2022-07-26T00:58:35.000Z\",\"monitoring\":{\"state\":\"disabled\"},\"placement\":{\"availabilityZone\":\"us-east-1a\",\"affinity\":null,\"groupName\":\"\",\"partitionNumber\":null,\"hostId\":null,\"tenancy\":\"default\",\"spreadDomain\":null,\"hostResourceGroupArn\":null},\"platform\":null,\"privateDnsName\":\"ip-172-31-22-225.ec2.internal\",\"privateIpAddress\":\"172.31.22.225\",\"productCodes\":[],\"publicDnsName\":\"ec2-3-80-54-200.compute-1.amazonaws.com\",\"publicIpAddress\":\"3.80.54.200\",\"ramdiskId\":null,\"state\":{\"code\":16,\"name\":\"running\"},\"stateTransitionReason\":\"\",\"subnetId\":\"subnet-0e3fa4706db12eaee\",\"vpcId\":\"vpc-07050ab479f8cc481\",\"architecture\":\"x86_64\",\"blockDeviceMappings\":[{\"deviceName\":\"/dev/xvda\",\"ebs\":{\"attachTime\":\"2022-07-26T00:58:36.000Z\",\"deleteOnTermination\":true,\"status\":\"attached\",\"volumeId\":\"vol-0ed49bc4c16d69029\"}}],\"clientToken\":\"\",\"ebsOptimized\":false,\"enaSupport\":true,\"hypervisor\":\"xen\",\"iamInstanceProfile\":null,\"instanceLifecycle\":null,\"elasticGpuAssociations\":[],\"elasticInferenceAcceleratorAssociations\":[],\"networkInterfaces\":[{\"association\":{\"carrierIp\":null,\"ipOwnerId\":\"amazon\",\"publicDnsName\":\"ec2-3-80-54-200.compute-1.amazonaws.com\",\"publicIp\":\"3.80.54.200\"},\"attachment\":{\"attachTime\":\"2022-07-26T00:58:35.000Z\",\"attachmentId\":\"eni-attach-067282ffe156d0a86\",\"deleteOnTermination\":true,\"deviceIndex\":0,\"status\":\"attached\",\"networkCardIndex\":0},\"description\":\"\",\"groups\":[{\"groupName\":\"launch-wizard-3\",\"groupId\":\"sg-0d992c24922ec4a34\"}],\"ipv6Addresses\":[],\"macAddress\":\"0a:51:12:23:ac:83\",\"networkInterfaceId\":\"eni-00ac815b08e1a96a4\",\"ownerId\":\"983960904967\",\"privateDnsName\":\"ip-172-31-22-225.ec2.internal\",\"privateIpAddress\":\"172.31.22.225\",\"privateIpAddresses\":[{\"association\":{\"carrierIp\":null,\"ipOwnerId\":\"amazon\",\"publicDnsName\":\"ec2-3-80-54-200.compute-1.amazonaws.com\",\"publicIp\":\"3.80.54.200\"},\"primary\":true,\"privateDnsName\":\"ip-172-31-22-225.ec2.internal\",\"privateIpAddress\":\"172.31.22.225\"}],\"sourceDestCheck\":true,\"status\":\"in-use\",\"subnetId\":\"subnet-0e3fa4706db12eaee\",\"vpcId\":\"vpc-07050ab479f8cc481\",\"interfaceType\":\"interface\"}],\"outpostArn\":null,\"rootDeviceName\":\"/dev/xvda\",\"rootDeviceType\":\"ebs\",\"securityGroups\":[{\"groupName\":\"launch-wizard-3\",\"groupId\":\"sg-0d992c24922ec4a34\"}],\"sourceDestCheck\":true,\"spotInstanceRequestId\":null,\"sriovNetSupport\":null,\"stateReason\":null,\"tags\":[{\"key\":\"Name\",\"value\":\"test\"},{\"key\":\"BackupSchedule\",\"value\":\"A\"}],\"virtualizationType\":\"hvm\",\"cpuOptions\":{\"coreCount\":1,\"threadsPerCore\":1},\"capacityReservationId\":null,\"capacityReservationSpecification\":{\"capacityReservationPreference\":\"open\",\"capacityReservationTarget\":null},\"hibernationOptions\":{\"configured\":false},\"licenses\":[],\"metadataOptions\":{\"state\":\"applied\",\"httpTokens\":\"optional\",\"httpPutResponseHopLimit\":1,\"httpEndpoint\":\"enabled\"},\"enclaveOptions\":{\"enabled\":false},\"bootMode\":null},\"supplementaryConfiguration\":{},\"tags\":{\"BackupSchedule\":\"A\",\"Name\":\"test\"},\"configurationItemVersion\":\"1.3\",\"configurationItemCaptureTime\":\"2022-07-26T19:43:33.411Z\",\"configurationStateId\":1658864613411,\"awsAccountId\":\"983960904967\",\"configurationItemStatus\":\"OK\",\"resourceType\":\"AWS::EC2::Instance\",\"resourceId\":\"i-06acc7778e56c246b\",\"resourceName\":null,\"ARN\":\"arn:aws:ec2:us-east-1:983960904967:instance/i-06acc7778e56c246b\",\"awsRegion\":\"us-east-1\",\"availabilityZone\":\"us-east-1a\",\"configurationStateMd5Hash\":\"\",\"resourceCreationTime\":\"2022-07-26T00:58:35.000Z\"},\"notificationCreationTime\":\"2022-07-26T19:45:35.232Z\",\"messageType\":\"ConfigurationItemChangeNotification\",\"recordVersion\":\"1.3\"}",
        "ruleParameters": "{\"BackupSchedule\":\"A,B,C\",\"exec_role\":\"arn:aws:iam::983960904967:role/configRemediationLambdaRole\",\"test1\":\"test1\",\"test2\":\"test2\",\"test3\":\"test3\",\"test4\":\"test4\",\"test5\":\"test5\",\"test6\":\"test6\",\"test7\":\"test7\",\"test8\":\"test8\",\"test9\":\"test9\",\"test10\":\"test10\",\"test11\":\"test11\",\"test12\":\"test12\",\"test13\":\"test13\",\"test14\":\"test14\",\"test15\":\"test15\"}",
        "resultToken": "eyJlbmNyeXB0ZWREYXRhIjpbLTEyOCw4MywtNTQsMCwtNDksLTg3LDQzLC0xMjcsNDIsLTMsLTExOSw3Nyw2OCw1OSwtOTksLTM2LDU4LC03MCwxMDMsOTIsODIsODksLTI3LDUyLDEwNSwzMywxMjUsLTI3LDU2LC0xMTUsMjIsMTE4LDEwNywtMjEsODUsMTgsMzgsMzUsLTgsLTEwLC0xMjUsLTk1LDI3LDEyMiwxMDYsMTA5LC02Niw5OSwyNywyMSw5NCwtMTgsLTYsNDEsLTgwLC0xNSwxMTUsMzEsNzAsMjMsLTEzLC02Myw1NSwxMTEsLTcxLC02MSwtNDUsLTQ3LC0yNSwtNzYsNSwtMTEsLTgyLC03OCw1NSwtNDYsODgsLTIyLC05LDIsMCwtNzMsOSwxMDYsOTUsODYsMzcsLTM3LDY4LC0xMDIsLTE4LC05NywzNiwtMTA3LC01LDEwNSwtMTI1LC0zMCwtNDAsMTE0LC0zNSwtNzUsNTgsNjIsMTIxLDIzLC03Nyw4MywtNjIsMzgsLTQ1LDk5LDUzLC0xMjgsMTUsLTExMiwtODMsNzYsNTgsLTEyNSwtMzQsMTI0LDY2LDY3LDExNiwyOSwtMTIxLC0xMCw3LDU0LC01NCwtODAsMTA3LDg5LDExNCwtNDAsLTYxLC0xMTIsMTA0LC0zOSwxMjUsMTAxLC0xMDksNTcsLTEwNiwtNjksOTcsLTYsLTEwNiw3OSwtMTA2LC02MywtNDMsLTc1LDcyLDE4LDQxLC0xMSwxMTcsMTAwLC0xMTMsMzYsOTEsLTQxLC0yOSwtODIsLTEyMywxMTksLTExMiw5MiwtNjIsODUsLTk3LDg0LDExMywxMDQsNDYsLTQyLDExOCw3LDg3LDExMSwtNDIsLTg5LDM0LC05NCwtMzksNDgsNiw1MywtODEsMzEsMTIwLC0xMDQsMjMsLTI3LDExMyw0OSw0OSw5MSwyLC0xMSwtMTA0LDI1LC01Myw4Miw3NCwtNCwyNiw3NiwtNSwtMzksLTg0LC02OSwxMTUsLTEwMCw2Myw1NiwtODAsMjYsLTk2LC0yOCwtODQsOTIsLTEyNCw4LC0yNSw3Nyw5Miw4MSw4OSw2NiwtMTE1LC03MSwxMDAsNjIsLTEyNSwtOTksLTc3LDEwOCw5NCwtNDcsLTYsODIsNDksLTkxLDEyMCw2NCw1MCw4NywtNjIsNDMsMTIzLDEwNiwtOTksODYsLTE1LDEyMCwtOTcsNjEsLTMwLDEyNyw1LDY2LC0xMTksLTQsLTkxLC01OCwxOCw0NCwtMTEyLDc4LC00LC0zNCw4NCwtMTI3LC02OSwtMTA5LC05NSw5NSwxMjQsLTE3LC04LC01OSw1OCwtMzgsLTEyMywtNzksNTgsMSwxNiwtMjUsLTMwLC02MiwtMTA1LDE3LC04MiwtNDMsLTY2LC02LC0xMjgsNzMsNzIsNzQsLTEwNiw0OSw1MiwtMTE2LDExOSwtNDEsLTExOSwxMDksLTE3LDE5LDcyLDU0LC0xMjIsMiwtODUsMjUsLTQxLC03NSw4MiwtOTcsOTAsLTEwMSw1MiwtOTYsLTQ1LC0yMCwtNjUsLTMxLC03MSw0MCw0MCw3OCwyNywzNCwtNjcsMTEyLDcyLC00NSwyMCwtMTE1LC0zOCwtMTIwLC04OSwxMjYsODIsMjUsOTIsNTQsLTk4LC0xMTgsLTg5LC0yOCwzLDQ5LDMwLC0xOSwtMTE4LDY0LC0xMjEsNzksLTExLDQ1LC02MSw5OSw2OCw2Niw5OCwtNDAsNTIsMzYsMjQsLTEwOSwtNywxMTQsLTEyNCwtMzYsLTE0LDI4LDAsLTc4LDQ0LC04OCwtODYsLTI2LDc5LC0yMiwtNjksMTUsMTAyLC0xMjQsLTg3LDQ1LC04NywtNjYsLTcsNiw2Miw3NSwtNzAsMTYsLTQzLDcxLC0xMCwtNDcsMCwtMSwtOSwxMjMsNDksODQsMzcsLTI1LDkzLDEyNCwtNDAsLTEwNiwxMjcsLTEwLC0xMTMsLTE0LC03Niw3MiwxMDksLTQ4LDExNCwtMzYsODYsLTc3LDQ3LDM3LC0xMTgsLTEyMyw5LDY5LDExNSwtNTEsLTU0LDg0LC0zNiwxMywtMTE2LC0xMiwzNSwxOCw0MSw4NCwwLDEwNCw4MSwtMjcsNzUsLTI2LC00Nyw3OCw3NSwzNCwtNTUsNzgsNTYsLTI4LDEwMywtODIsMTEyLDkxLC0xMTksNDAsNjMsLTEwMCwtNTQsLTEwMyw1Nyw5OSwxMjQsLTE2LDY2LDEwNCwtNTIsLTIwLDk0LC00LDM1LDExMSwtMTEzLC0xMjIsMTE0LDQzLC01MiwtMTEsLTkwLC05NSwtMjMsLTM2LC0xMTMsNzksODAsLTE1LDIwLDExMywzOCwtNjMsLTcsLTMyLDEwOCwtNDgsLTQ1LDExNSwtOSwtMTAsMTE5LC0xMDgsLTQ3LC0xMDAsLTYzLC00NiwtMTksNTIsLTExLC05MCw4OSwtODgsNjUsLTQ4LDc3LDI0LDQsODMsMjgsLTM5LDEzLDMxLDEwOSwtODUsMywxMTQsNDIsLTExMywtMTAyLDExNywyOSwtMSw1LDk0LDQxLDEyNCwtMTMsMTI3LC05MiwxMTEsLTI5LDc0XSwibWF0ZXJpYWxTZXRTZXJpYWxOdW1iZXIiOjEsIml2UGFyYW1ldGVyU3BlYyI6eyJpdiI6WzEyMiwtNTEsODksLTk4LDYwLC05MywtMjksMTI0LDEwNCwxMDUsMzksMCw4MCwtNDMsLTk4LC0yNl19fQ==",
        "eventLeftScope": 'false',
        "executionRoleArn": "arn:aws:iam::983960904967:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig",
        "configRuleArn": "arn:aws:config:us-east-1:983960904967:config-rule/config-rule-cr3nbj",
        "configRuleName": "required_tag_remediation",
        "configRuleId": "config-rule-cr3nbj",
        "accountId": "1234567890"
    }

    context = {}

    lambda_handler(event, context)


if __name__ == "__main__":
    main()
