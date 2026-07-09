from rest_registration.api.views.register import RegisterView
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.http import Http404
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.models import User
from common.api.pagination import StandardPagination
from account.models import Account, Document
from account.serializers import RegisterSerializer, AccountSerializer, AccountUpdateSerializer, DocumentSerializer


class RegisterView(RegisterView):
    permission_classes = []
    authentication_classes = []
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


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer
    queryset = Document.objects.none()
    lookup_field = 'uuid'
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'uuid']
    ordering_fields = ['order']

    def get_queryset(self):
        return self.request.user.documents.all()

    def get_document_object(self, uuid):
        qs = self.get_queryset()
        try:
            return qs.get(uuid=uuid)
        except Document.DoesNotExist:
            raise Document.DoesNotExist


@api_view(['POST'])
@permission_classes([])
@authentication_classes([])
def seed_e2e_user(request):
    """
    Idempotently create/reset an e2e test user for Playwright test suites.
    Only available in debug mode (local/CI environments).
    """
    if not settings.DEBUG:
        return Response(status=404)

    email = 'e2e-test@acrylic.la'
    password = 'E2eTestPass123!'
    user, _ = User.objects.get_or_create(username=email, defaults={'email': email})
    user.set_password(password)
    user.save()
    Account.objects.get_or_create(user=user, defaults={'user_type': Account.UserType.CLUB})
    return Response({'detail': f'Seeded e2e test user: {email}'})
