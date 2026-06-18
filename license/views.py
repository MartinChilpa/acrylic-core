from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from license.models import License
from license.serializers import LicenseSerializer


class LicenseViewSet(viewsets.ModelViewSet):
    serializer_class = LicenseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        """Return only licenses for the current user's club."""
        user = self.request.user
        if hasattr(user, 'club') and user.club:
            return License.objects.filter(club=user.club)
        return License.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a new license request."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, uuid=None):
        """
        Update license status. Only callable via internal API with WHITELIST_INTERNAL_TOKEN.
        Called by Lambda after distributor replies to email.
        """
        # Verify internal token
        token = request.META.get('HTTP_X_INTERNAL_TOKEN', '')
        expected_token = settings.WHITELIST_INTERNAL_TOKEN
        if not expected_token or token != expected_token:
            return Response(
                {"detail": "Invalid or missing internal token."},
                status=status.HTTP_403_FORBIDDEN
            )

        license_obj = self.get_object()
        new_status = request.data.get('status')

        # Validate status
        valid_statuses = [License.STATUS_APPROVED, License.STATUS_REJECTED]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only allow transitions from pending
        if license_obj.status != License.STATUS_PENDING:
            return Response(
                {"detail": f"Cannot update status from {license_obj.status}. Only pending licenses can be updated."},
                status=status.HTTP_400_BAD_REQUEST
            )

        license_obj.status = new_status
        license_obj.save()

        serializer = self.get_serializer(license_obj)
        return Response(serializer.data)
