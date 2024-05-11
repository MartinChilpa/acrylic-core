from rest_registration.api.views.register import RegisterView
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import Http404
from django.shortcuts import render
from account.models import Account
from account.serializers import RegisterSerializer, AccountSerializer, AccountUpdateSerializer


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

    @action(detail=False, methods=['get', 'put'])
    def profile(self, request):
        """
        Retrieve or update the user account data.
        """
        instance = self.get_object()

        if request.method == 'GET':
            serializer = AccountSerializer(instance)
            return Response(serializer.data)
    
        elif request.method == 'PUT':
            serializer = AccountUpdateSerializer(instance, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
