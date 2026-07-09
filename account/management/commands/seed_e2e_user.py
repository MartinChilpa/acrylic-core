from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from account.models import Account


class Command(BaseCommand):
    help = "Idempotently creates/resets the e2e test user for Playwright suites."

    def handle(self, *args, **options):
        email = "e2e-test@acrylic.la"
        password = "E2eTestPass123!"
        user, _ = User.objects.get_or_create(username=email, defaults={"email": email})
        user.set_password(password)
        user.save()
        Account.objects.get_or_create(user=user, defaults={"user_type": Account.UserType.CLUB})
        self.stdout.write(self.style.SUCCESS(f"Seeded e2e test user: {email}"))
