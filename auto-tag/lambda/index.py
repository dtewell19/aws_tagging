from __future__ import print_function
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # logger.info(Event:  + str(event))
    # print(Received event:  + json.dumps(event, indent=2))

    ids = []

    try:
        detail = event['detail']
        eventname = detail['eventName']
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        userType = detail['userIdentity']['type']

        if userType == "IAMUser":
            user = detail['userIdentity']['userName']

        else:
            user = principal.split(":")[1]

        logger.info("principalId: " + str(principal))
        logger.info("eventName: " + str(eventname))
        logger.info("detail: " + str(detail))

        if not detail['responseElements']:
            logger.warning("Not responseElements found")
            if detail['errorCode']:
                logger.error("errorCode: " + detail['errorCode'])
            if detail['errorMessage']:
                logger.error("errorMessage: " + detail['errorMessage'])
            return False

        ec2 = boto3.resource('ec2')

        if eventname == "CreateVolume":
            ids.append(detail['responseElements']['volumeId'])
            logger.info(ids)

        elif eventname == "RunInstances":
            items = detail['responseElements']['instancesSet']['items']
            for item in items:
                ids.append(item['instanceId'])
                add_root_volume_tags(item['instanceId'])
            logger.info(ids)
            logger.info("number of instances: " + str(len(ids)))

            base = ec2.instances.filter(InstanceIds=ids)

            # loop through the instances
            for instance in base:
                for vol in instance.volumes.all():
                    ids.append(vol.id)
                for eni in instance.network_interfaces:
                    ids.append(eni.id)

        elif eventname == "CreateImage":
            ids.append(detail['responseElements']['imageId'])
            logger.info(ids)

        elif eventname == "CreateSnapshot":
            ids.append(detail['responseElements']['snapshotId'])
            logger.info(ids)
        else:
            logger.warning("Not supported action")

        if ids:
            for resourceid in ids:
                print("Tagging resource" + resourceid)
            ec2.create_tags(Resources=ids, Tags=[
                {
                    "Key": "Owner",
                    "Value": user
                },
                {
                    "Key": "PrincipalId",
                    "Value": principal
                }]
            )

        return True
    except Exception as e:
        logger.error("Something went wrong: " + str(e))
        return False


def add_root_volume_tags(instance_id):

    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id)
    ec2tags = instance.tags
    logging.info('Instance Tags:' + str(ec2tags))

    for volume in instance.volumes.all():
        logging.info('Volume Id: ' + str(volume))
    #    Create tags on volume if they don't match the instance
        if volume.tags != ec2tags:
            logging.warn("Tags don't match. Updating... ")
            # remove aws tags
            tag_list = []

            for tag in ec2tags:
                if not tag['Key'].startswith('aws'):
                    tag_list.append(tag)

            volume.create_tags(DryRun=False, Tags=tag_list)
            logging.warn("Volume " + str(volume) +
                         "updated with tags: " + str(volume.tags))
