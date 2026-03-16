"""A utility module which, if run on a linux system which provides a /usr/bin/mail function, sends mails to given recipients.

"""

import platform

import subprocess
from datetime import datetime as dt

def send_mail(subject: str, recipients_comma_separated: str, body: str) -> tuple:
    """On a linux system, using the built-in mail function, send an e-mail; returns exit code (0=success, 1=failure) and a short message."""
    if "linux" in platform.system().lower():
        try:
            message = f"""To: {recipients_comma_separated}\nSubject: {subject}\nContent-Type: text/html\n\n""" + \
            f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{subject}</title></head>""" + \
                       f"""<body>{body}</body></html>"""

            process = subprocess.Popen(
                ['/usr/sbin/sendmail', '-t'],
                stdin=subprocess.PIPE,
                universal_newlines=True
            )

            # Send the email content
            process.communicate(message)

            # Check if sendmail was successful
            if process.returncode != 0:
                return 1, f"send_mail() ERROR: Failed to send email, returncode: {process.returncode}."
            else:
                return 0, f"Email sent successfully, subject: {subject}, {len(message)} bytes."

        except Exception as e:
            return 1, f"send_mail() ERROR: {e}"
    else:
        return 1, f"WARN: This is not a Linux system, no mail function implemented, ignoring mail '{subject}\n{recipients_comma_separated}\n{body}"



def recipients_that_are_now_is_in_allowed_time_window(allowed_times: dict, recipients_comma_separated: str, date_and_time = dt.now()) -> str:
    """based on the configuration in allowed_times, find those recipients which want to receive alerts 'now'."""
    weekday = date_and_time.strftime("%A")
    current_time = date_and_time.strftime("%H:%M:%S")
    recipients = recipients_comma_separated.split(',')
    allowed_recpients = []
    if allowed_times:
        default_allowance = False
        if allowed_times.get(weekday):
            time_of_day_range = allowed_times[weekday]
            if time_of_day_range[0] <= current_time < time_of_day_range[1]:
                default_allowance = True
        for recipient in recipients:
            allowed_times_for_recipient = allowed_times.get(recipient)
            if allowed_times_for_recipient:
                if allowed_times_for_recipient.get(weekday):
                    time_of_day_range = allowed_times_for_recipient[weekday]
                    if time_of_day_range[0] <= current_time < time_of_day_range[1]:
                        allowed_recpients.append(recipient)
            elif default_allowance:
                allowed_recpients.append(recipient)
        return ','.join(allowed_recpients)
    else:
        return ""




if __name__ == "__main__":
    print(send_mail("My Test", "markus.meier-trost@sbb.ch", """<h1 style="color: blue;">Hallo!</h1><p>Das ist <strong>rich</strong> text von Linux.</p>"""))
