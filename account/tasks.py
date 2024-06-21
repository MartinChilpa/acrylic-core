from django.conf import settings
from django.core.mail import send_mail


def send_registration_invite(email):
    signup_url = f'{settings.FRONTEND_BASE_URL}auth/sign-up'

    subject = "You've been invited to Acrylic.la"
    message = f"""
    You have been invited to sign up to Acrylic.la on {signup_url}
    """    
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
