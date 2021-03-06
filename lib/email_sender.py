import collections
import datetime
from email.mime.text import MIMEText
import lib.email_auth as email_auth

TODAY = datetime.datetime.now().strftime("%Y-%m-%d")


class EmailSender:

  def __init__(self, email_config) -> None:
    self.email_config = email_config

  def send_email(self, groups_dict) -> None:
    email_content = self.create_email_content(groups_dict)
    self.send_email_content("Tracking Numbers " + TODAY, email_content)

  def create_email_content(self, trackings) -> str:
    groups_dict = collections.defaultdict(list)
    for tracking in trackings:
      groups_dict[tracking.group].append(tracking)

    content = "Tracking number / order number(s) per group:\n\n"
    for group, trackings in groups_dict.items():
      numbers = [
          f"{tracking.tracking_number} / {', '.join(tracking.order_ids)} / {tracking.to_email} / {tracking.items}"
          for tracking in trackings
      ]
      content += f"{group} ({len(numbers)}):\n"
      content += '\n'.join(numbers)
      content += '\n\n'

    content += "These are the new tracking numbers that we have found. See the Google Sheet for all tracking numbers."
    return content

  def send_email_content(self, subject, content, recipients=[]) -> None:
    recipients = recipients if recipients else [self.email_config['username']]

    message = MIMEText(content)
    message['From'] = self.email_config['username']
    message['To'] = ", ".join(recipients)
    message['Subject'] = subject
    email_auth.send_email(recipients, message)
