from django.db.models.signals import post_save
from django.dispatch import receiver
from account.models import Invitation
from account.tasks import send_registration_invite


@receiver(post_save, sender=Invitation)
def invitation_created(sender, instance, created, **kwargs):
    """ when an artist is created """
    if created:
            # send inivitation email
            send_registration_invite(instance.email)
