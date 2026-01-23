"""A utility module which, if run on a linux system which provides a /usr/bin/mail function, sends mails to given recipients.

"""

import platform

import subprocess


def send_mail(subject: str, recipients_comma_separated: str, body: str) -> None:
    """On a linux system, using the built-in mail function, send an e-mail."""
    if "linux" in platform.system().lower():
        try:
            message = f"""To: {recipients_comma_separated}\nSubject: {subject}\nContent-Type: text/html\n\n""" + \
            f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{subject}</title></head>""" + \
                       f"""<body>{body}</body></html>"""

            process = subprocess.Popen(
                ['sendmail', '-t'],
                stdin=subprocess.PIPE,
                universal_newlines=True
            )

            # Send the email content
            process.communicate(message)

            # Check if sendmail was successful
            if process.returncode != 0:
                print("Failed to send email.")
            else:
                print("Email sent successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print(f"WARN: This is not a Linux system, no mail function implemented, ignoring mail '{subject}'.")
        print("Subject:", subject)
        print("Body:")
        print(body)


if __name__ == "__main__":
    send_mail("My Test", "markus.meier-trost@sbb.ch", """<h1 style="color: blue;">Hallo!</h1><p>Das ist <strong>rich</strong> text von Linux.</p>""")
