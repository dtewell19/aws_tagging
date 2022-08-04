# SCP Tag Enforcement

This example shows how to enforce tags on creation. It flows the design displayed [here](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples_tagging.html).


### Warning

Cloudformation does not currently support tagging of the EC2 root volume. This breaks the example SCP code for `"arn:aws:ec2:*:*:volume/*"`. 


     {
        "Sid": "DenyRunInstanceWithNoProjectTag",
        "Effect": "Deny",
        "Action": "ec2:RunInstances",
        "Resource": [
            "arn:aws:ec2:*:*:instance/*",
            "arn:aws:ec2:*:*:volume/*"
        ],
        "Condition": {
            "Null": {
            "aws:RequestTag/Project": "true"
            }
        }
        }

However, SCPs can be applied to all additional volumes created with `ec2:CreateVolume`

    {
        "Sid": "DenyCreateVolumesWithNoTags",
        "Effect": "Deny",
        "Action": "ec2:CreateVolume",
        "Resource": [
        "arn:aws:ec2:*:*:volume/*"
        ],
        "Condition": {
        "Null": {
            "aws:RequestTag/Project": "true",
            "aws:RequestTag/CostCenter": "true"
        }
        }
    }