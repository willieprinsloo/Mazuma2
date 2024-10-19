import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = 'sendgrid.env'


def sendMail(cfrom_email, cto_email, csubject, ccontent):
    message = Mail(
        from_email=cfrom_email,
        to_emails=cto_email,
        subject=csubject,
        html_content=ccontent)

    try:
        sg = SendGridAPIClient('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')
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print("Mailed failed with error")
        print(e)


#sendMail('ivan@reboxed.co', 'prinsloo.willie@gmail.com', 'test 1', 'test 2')
