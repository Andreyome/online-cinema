from aiosmtplib import send
from email.message import EmailMessage
from src.config.settings import settings

# async def send_email(to: str, subject: str, body: str):
#     message = EmailMessage()
#     message["From"] = settings.SMTP_FROM
#     message["To"] = to
#     message["Subject"] = subject
#     message.set_content(body, subtype="html")
#     await send(message,
#                hostname=settings.SMTP_HOST,
#                port=settings.SMTP_PORT,
#                username=settings.SMTP_USER,
#                password=settings.SMTP_PASSWORD,
#                start_tls=True)
