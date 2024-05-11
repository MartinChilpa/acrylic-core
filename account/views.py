from rest_registration.api.views.register import RegisterView
from django.shortcuts import render
from account.serializers import RegisterSerializer


class RegisterView(RegisterView):
    serializer_class = RegisterSerializer
