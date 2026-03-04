


from django.dispatch import receiver
from django.db.models.signals import post_save
from club.models import Club
from club.tasks import send_registration_invite



@receiver(post_save, sender=Club)
def club_created(sender, instance, created, **kwargs):
    if created:
        if instance.user:
            email_user= instance.user.email
            send_registration_invite(email_user)
