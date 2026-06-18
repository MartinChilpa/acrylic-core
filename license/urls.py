from django.urls import path, include
from rest_framework.routers import DefaultRouter

from license.views import LicenseViewSet

router = DefaultRouter()
router.register(r'licenses', LicenseViewSet, basename='license')

urlpatterns = [
    path('my-club/', include(router.urls)),
]
