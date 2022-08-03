# import json
# import boto3
# import logging
# from botocore.exceptions import ClientError

# ## configuratuion notes
# #   recipient and sender need to be replaced below with correct SES values


# def send_violation_email(configuration_item, current_tags, violation):
#     sender = "drew.tewell@slalom.com"  # replace with correct SES configuration
#     # requires CreatorName to be present
#     recipient = current_tags['CreatorName']
#     charset = "UTF-8"
#     subject = "Non-Compliant Resource Tag (" + \
#         configuration_item["resourceId"] + ")"
#     body_text = ("Non-Compliant Resource Tag\r\n" + "Resource Id: " +
#                  configuration_item["resourceId"] + "\r\n" + "Violation: " + violation)

#     client = boto3.client('ses')
#     try:
#         # Provide the contents of the email.
#         response = client.send_email(
#             Destination={
#                 'ToAddresses': [
#                     recipient,
#                 ],
#             },
#             Message={
#                 'Body': {
#                     'Text': {
#                         'Charset': charset,
#                         'Data': body_text,
#                     },
#                 },
#                 'Subject': {
#                     'Charset': charset,
#                     'Data': subject,
#                 },
#             },
#             Source=sender,
#         )
#     # Display an error if something goes wrong.
#     except ClientError as e:
#         print(e.response['Error']['Message'])
#     else:
#         logging.info("Email sent! Message ID:"),
#         logging.info(response['MessageId'])

#     return response


# def send_remediation_email(arn, current_tags, status):
#     sender = "drew.tewell@slalom.com"  # replace with correct SES configuration
#     # requires CreatorName to be present
#     recipient = current_tags['CreatorName']
#     charset = "UTF-8"
#     subject = "Remediated Non-Compliant Resource Tag (" + \
#         str(arn) + ")"
#     body_text = ("Non-Compliant Resource Tag\r\n" + "Resource Id: " +
#                  str(arn) + "\r\n" + "Status: " + status
#                  + "\r\n")

#     client = boto3.client('ses')
#     try:
#         # Provide the contents of the email.
#         response = client.send_email(
#             Destination={
#                 'ToAddresses': [
#                     recipient,
#                 ],
#             },
#             Message={
#                 'Body': {
#                     'Text': {
#                         'Charset': charset,
#                         'Data': body_text,
#                     },
#                 },
#                 'Subject': {
#                     'Charset': charset,
#                     'Data': subject,
#                 },
#             },
#             Source=sender,
#         )
#     # Display an error if something goes wrong.
#     except ClientError as e:
#         print(e.response['Error']['Message'])
#     else:
#         logging.info("Email sent! Message ID:"),
#         logging.info(response['MessageId'])

#     return response
