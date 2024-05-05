from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers
from rest_registration.api import views as registration_views
API_VERSION = 'v1'

from artist import views as artist_views
from catalog import views as catalog_views
from content import views as content_views
from legal import views as legal_views
from legal import webhooks as legal_webhooks


router = routers.DefaultRouter()
router.register('artists', artist_views.ArtistViewSet)
router.register('tracks', catalog_views.TrackViewSet)
router.register('genres', catalog_views.GenreViewSet)
#router.register('distributors', catalog_views.DistributorViewSet)
router.register('distributors', catalog_views.DistributorSerializer)
router.register('synclists', catalog_views.SyncListViewSet)
router.register('articles', content_views.ArticleViewSet)

# artist dashboard
router.register('my-artist', artist_views.MyArtistViewSet)
router.register('my-artist/tracks', catalog_views.MyTrackViewSet)
#router.register(r'my-artist/tracks/(?P<track_id>\d+)/master-splits', legal_views.MasterSplitViewSet, basename='master-split')
router.register('my-artist/synclists', catalog_views.MySyncListViewSet)


registration_urls = (
    [
        #path('register/', registration_views.register, name='register'),
        #path('verify-registration/', registration_views.verify_registration, name='verify-registration'),

        path('send-reset-password-link/', registration_views.send_reset_password_link, name='send-reset-password-link'),
        path('reset-password/', registration_views.reset_password, name='reset-password'),

        #path('login/', registration_views.login, name='login'),
        #path('logout/', registration_views.logout, name='logout'),

        #path('profile/', registration_views.profile, name='profile'),

        path('change-password/', registration_views.change_password, name='change-password'),

        #path('register-email/', registration_views.register_email, name='register-email'),
        path('verify-email/', registration_views.verify_email, name='verify-email'),
    ],
    'rest_registration',
)


urlpatterns = [
    path('admin/', admin.site.urls),

    # API urls
    path(f'api/{API_VERSION}/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'api/{API_VERSION}/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    
    path(f'api/{API_VERSION}/', include([
        # JWT authentication
        path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        # path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

        # API social auth
        path('auth/', include('rest_social_auth.urls_jwt_pair')),
        path('account/', include(registration_urls)),
        
        # Registration
        #path('account/', include('rest_registration.api.urls')),

        # 
        path('artists/register/', artist_views.ArtistRegisterView.as_view(), name='artist_register_view'),
    
        # Artist dashboard URLs
        

        # Application
        path('', include(router.urls)),

        
        # Accounts
        #path('account/profile/', profile, name='profile'),
        # Registration
        #path('account/', include('rest_registration.api.urls')),
    ])),

    # Dropbox Sign
    path(f'legal/webhooks/dropbox-sign/', legal_webhooks.hellosign_webhook, name='dropbox_sign_webhook'),

]


#router = routers.SimpleRouter()
#router.register(f'api/{API_VERSION}/library/category', library_views.CategoryViewSet, basename='category')


