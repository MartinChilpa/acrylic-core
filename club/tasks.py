

from django.conf import settings
import urllib.parse
from django.core.mail import send_mail


def send_registration_invite(email):
    signup_url = f'{settings.FRONTEND_BASE_URL}auth/sign-up'
    email_string = urllib.parse.quote_plus(email)

    
    subject=f"Welcome to Acrylic"

    message=f"""
            Dear [Football Club / League / Athlete Name],

            Welcome to Acrylic:lizard:! We're thrilled to have you on board.

            Your account has been successfully set up and your personalized dashboard is ready to go. It's time to grow your audience with real music.

            Use the credentials below to get started:

                Access URL: 
                Email Address:
                Temporary Password:

            For security reasons, you will be prompted to change this password upon your first login.

            If you have any questions or need help getting started, reach out to your representative. We're here for you!


            """
    send_mail(subject,message, settings.DEFAULT_FROM_EMAIL,[email],fail_silently=False)
