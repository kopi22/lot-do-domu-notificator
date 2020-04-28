import sys
import time
import re
from string import Template

# Scheduler
import schedule

# HTTP requests
import requests

# MAIL CREATION
import base64
from email.mime.text import MIMEText

# GOOGLE GMAIL API
import pickle
import os.path
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

gmail_user = 'your.email@gmail.com'     # INIT

NOTIFICATION_SUBJECT_TEMPLATE = Template('#LotDoDomu - Tickets from $origin to $des')
NOTIFICATION_MESSAGE_TEMPLATE = Template('Tickets are online, available at: $link')

TARGET_AIRPORTS = []


def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
    return {
        'raw': raw_message.decode("utf-8")
    }


def send_message(service, user_id, message):
    """Send an email message.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      message: Message to be sent.

    Returns:
      Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Notification sent! Message Id: {}'.format(message['id']))
        return message
    except errors.HttpError as error:
        print('An error occurred: {}'.format(error))


def notify(subject, content):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    message = create_message(gmail_user, gmail_user, subject, content)
    send_message(service, 'me', message)


def findFlights():
    global TARGET_AIRPORTS

    print('New Report:')
    request = requests.get('https://www.lot.com/pl/pl/lot-do-domu')
    if request:
        content = request.text
    else:
        print('Report Failed')
        return

    flightRegex = re.compile(r'departureAirport=([a-zA-Z]+)&amp;destinationAirport=([a-zA-Z]+)&amp;departureDate=(\d+)')
    flights = re.findall(flightRegex, content)
    for f, t, d in flights:
        print(f + ' to ' + t + ' on ' + d[:2] + ' of March')
        if f in TARGET_AIRPORTS:
            url = 'https://www.lot.com?departureAirport=' + f + '&destinationAirport=' + t + '&departureDate=' + d
            notify(NOTIFICATION_SUBJECT_TEMPLATE.substitute(des=f), NOTIFICATION_MESSAGE_TEMPLATE.substitute(link=url))
            TARGET_AIRPORTS.remove(f)

    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: main.py <TARGET_AIRPORT_IATA_CODES> ...')

    print("I'm looking for connections from: ")
    for iata in sys.argv[1:]:
        print(iata)
        TARGET_AIRPORTS.append(iata)

    # Scheduler is not necessary, but I wanted to try it
    schedule.every().minute.do(findFlights)
    findFlights()

    while 1:
        schedule.run_pending()
        time.sleep(30)
