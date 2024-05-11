from rest_registration.api.views.register import RegisterView
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import Http404
from django.shortcuts import render
from account.models import Account
from account.serializers import RegisterSerializer, AccountSerializer


class RegisterView(RegisterView):
    serializer_class = RegisterSerializer


class AccountViewSet(viewsets.GenericViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.none()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        instance = getattr(self.request.user, 'account', None)
        if not instance:
            raise Http404('No Account instance found.')
        return instance

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """
        Retrieve the singleton instance.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)