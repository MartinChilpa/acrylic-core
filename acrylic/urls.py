from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_registration.api import views as registration_views
API_VERSION = 'v1'

from common import views as common_views
from account import views as account_views
from artist import views as artist_views
from catalog import views as catalog_views
from content import views as content_views
from legal import views as legal_views
from legal import webhooks as legal_webhooks
from spotify import views as spotify_views
from aims import views as aims_views
from aims import webhooks as aims_webhooks
from label import views as label_views
from club import views as club_views


router = routers.DefaultRouter()

# common public views
router.register('countries', common_views.CountryViewSet, basename='country')

# public views
router.register('artists', artist_views.ArtistViewSet)
router.register('tracks', catalog_views.TrackViewSet)
router.register('genres', catalog_views.GenreViewSet)
router.register('distributors', catalog_views.DistributorViewSet)
router.register('synclists', catalog_views.SyncListViewSet)
router.register('prices', catalog_views.PriceViewSet)
router.register('articles', content_views.ArticleViewSet)
router.register('teams', club_views.TeamViewSet, basename='teams')

# spotify views
router.register('spotify/track/preview', spotify_views.TrackPreviewViewSet, basename='simple')

# global account
router.register('account', account_views.AccountViewSet)
router.register('account/documents', account_views.DocumentViewSet)

# artist account
router.register('my-artist', artist_views.MyArtistViewSet)
router.register('my-artist/tracks', catalog_views.MyTrackViewSet)
router.register('my-artist/synclists', catalog_views.MySyncListViewSet)
router.register('my-artist/split-sheets', legal_views.MySplitSheetViewSet)
router.register('my-artist/prices', catalog_views.MyPriceViewSet)

# aims
router.register('aims/similarity',aims_views.SimilarityViewSet,  basename='aims-similarity')
router.register('aims/similarity-prompt', aims_views.SimilarityPromptViewSet, basename='aims-similarity-prompt')
router.register('aims/similarity-video', aims_views.SimilarityVideoViewSet, basename='aims-similarity-video')


# buyer account
# tbd


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
        path('verify-user/', registration_views.verify_registration, name='verify-user'),
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
        
        # account registration
        path('account/register/', account_views.RegisterView.as_view(), name='artist_register_view'),
    
        # Artist dashboard URLs
        

        # Application
        path('aims/download-url/', aims_views.AimsDownloadUrlView.as_view(), name='aims_download_url'),
        path('', include(router.urls)),

        # Ingestion (CSV preview)
        path('ingestion/upload_csv/', label_views.UploadCsvPreviewView.as_view(), name='upload_csv_preview'),
        path('ingestion/save_artists/', label_views.SaveArtistsView.as_view(), name='save_artists'),
        # Ingestion (bulk track upload for labels)
        path(
            'ingestion/save_tracks/',
            catalog_views.TrackViewSet.as_view(
                {'post': 'save_to_s3_bulk'},
                authentication_classes=[BasicAuthentication, JWTAuthentication],
                permission_classes=[IsAuthenticated],
            ),
            name='save_tracks',
        ),

        
        # Accounts
        #path('account/profile/', profile, name='profile'),
        # Registration
        #path('account/', include('rest_registration.api.urls')),
    ])),

    # Dropbox Sign
    path(f'legal/webhooks/signwell/', legal_webhooks.signwell_webhook, name='sign_webhook'),
    # AIMS webhooks (track processing)
    path('aims-webhook', aims_webhooks.AimsWebhookView.as_view(), name='aims_webhook_no_slash'),
    path('aims-webhook/', aims_webhooks.AimsWebhookView.as_view(), name='aims_webhook'),

]


#router = routers.SimpleRouter()
#router.register(f'api/{API_VERSION}/library/category', library_views.CategoryViewSet, basename='category')
