import os
import boto3
from aiosmtpd.controller import Controller
from email.parser import BytesParser
from email.policy import default
from botocore.exceptions import ClientError

# --- Configuration ---
AWS_REGION = "af-south-1"  # e.g., us-east-1
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 1025

class SESForwarderHandler:
    def __init__(self):
        # Initialize the SES client
        self.ses_client = boto3.client('ses', region_name=AWS_REGION)

    async def handle_DATA(self, server, session, envelope):
        """
        This method is called when the SMTP 'DATA' command is received.
        """
        peer = session.peer
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        raw_data = envelope.content  # This is the full raw RFC822 message

        print(f"Receiving message from {peer}")
        print(f"Forwarding mail from {mail_from} to {rcpt_tos}")

        try:
            # Forward the raw message directly to SES
            response = self.ses_client.send_raw_email(
                Source=mail_from,
                Destinations=rcpt_tos,
                RawMessage={
                    'Data': raw_data
                }
            )
            print(f"Successfully sent! Message ID: {response['MessageId']}")
        except ClientError as e:
            print(f"Error sending via SES: {e.response['Error']['Message']}")
            return '550 Error: Message rejected by AWS SES'
        
        return '250 OK'

if __name__ == '__main__':
    handler = SESForwarderHandler()
    controller = Controller(handler, hostname=LISTEN_HOST, port=LISTEN_PORT)
    
    print(f"SMTP to SES Bridge started on {LISTEN_HOST}:{LISTEN_PORT}")
    controller.start()
    
    try:
        # Keep the script running
        input("Press Enter to stop the server...\n")
    finally:
        controller.stop()
