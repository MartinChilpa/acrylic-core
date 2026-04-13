from django.contrib.auth.models import User
from rest_framework import serializers

class EmailAuthBackend:
    """
    Authenticate using an e-mail address.
    """
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email=username)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None
            
        if not user.check_password(password):
                return None
        
        account = user.account

        if account.user_type == "ARTIST" and not account.contract_signed:
            raise serializers.ValidationError(
                {"detail": "The contract has not been signed."}
            )
        return user
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
