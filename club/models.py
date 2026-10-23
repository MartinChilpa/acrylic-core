from django.conf import settings
from django.db import models
from common.models import BaseModel
from django.utils.text import slugify
from django.db.models import Q
from django_countries.fields import CountryField

from catalog.models import Track

# Create your models here.
class Club(BaseModel):
    # Relación con la cuenta (quién administra este club)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='club', blank=True, null=True)
    
    # Campos básicos solicitados
    club_name = models.CharField(max_length=150, verbose_name="Nombre del Club")

    # ISO-3166 alpha-2 country code (e.g. "US", "MX")
    country = CountryField(max_length=2, blank=True)
    
    stadium_name = models.CharField(max_length=150, blank=True, verbose_name="Estadio")
    portal_web = models.URLField(max_length=255, blank=True, verbose_name="Sitio Web")
    
    # Campo extra para el dashboard (slug único para la URL del portal)
    slug = models.SlugField(max_length=100, blank=True)

    # Team/Club UI config (for frontend theming)
    team_name = models.CharField(max_length=150, blank=True, default="")
    tagline = models.CharField(max_length=250, blank=True, default="")
    colors = models.JSONField(null=True, blank=True, default=dict)
    auth_promo = models.JSONField(null=True, blank=True, default=dict)
    sidenav = models.JSONField(null=True, blank=True, default=dict)

    # Social media URLs for whitelisting requests
    instagram_url = models.URLField(max_length=255, blank=True, default="")
    tiktok_url = models.URLField(max_length=255, blank=True, default="")
    youtube_url = models.URLField(max_length=255, blank=True, default="")

    # Estado operativo
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        constraints = [
            models.UniqueConstraint(
                fields=['slug'], 
                name='unique_club_slug',
                condition=~Q(slug='')
            )
        ]

    def __str__(self):
        return self.club_name
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if missing.
        if not self.slug:
            base = slugify(self.club_name)
            slug = base
            same_slug_clubs = Club.objects.filter(slug=slug).exclude(uuid=self.uuid).count()
            if same_slug_clubs > 0:
                slug = f"{base}{same_slug_clubs + 1}"
            self.slug = slug
            
        super(Club, self).save(*args, **kwargs)


class Player(BaseModel):
    club = models.ForeignKey(Club, related_name="players", on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    nationality = CountryField(max_length=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=["club", "name"]),
        ]

    def __str__(self) -> str:
        return self.name


class TrackFavorite(BaseModel):
    club = models.ForeignKey(Club, related_name="track_favorites", on_delete=models.CASCADE)
    track = models.ForeignKey(Track, related_name="club_favorites", on_delete=models.CASCADE)

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.UniqueConstraint(fields=["club", "track"], name="unique_club_track_favorite")
        ]
        indexes = BaseModel.Meta.indexes + [
            models.Index(fields=["club", "track"]),
        ]

    def __str__(self) -> str:
        return f"{self.club_id}:{self.track_id}"


class TrackPublishedLink(BaseModel):
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        YOUTUBE_SHORTS = "youtube_shorts", "YouTube Shorts"
        FACEBOOK = "facebook", "Facebook"

    club = models.ForeignKey(
        Club,
        related_name="published_track_links",
        on_delete=models.CASCADE,
    )
    track = models.ForeignKey(
        Track,
        related_name="club_published_links",
        on_delete=models.CASCADE,
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    url = models.URLField(max_length=2048)

    class Meta:
        ordering = ["platform", "-created"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "track", "url"],
                name="uniq_club_track_pub_url",
            ),
        ]
        indexes = BaseModel.Meta.indexes + [
            models.Index(
                fields=["club", "track", "platform"],
                name="club_pub_cl_tr_plat_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.club_id}:{self.track_id}:{self.platform}"
