from django.conf import settings
from django.db import models
from common.models import BaseModel
from django.utils.text import slugify
from django.db.models import Q

# Create your models here.
class Club(BaseModel):
    # Relación con la cuenta (quién administra este club)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='club', blank=True, null=True)
    
    # Campos básicos solicitados
    club_name = models.CharField(max_length=150, verbose_name="Nombre del Club")
    
    stadium_name = models.CharField(max_length=150, blank=True, verbose_name="Estadio")
    portal_web = models.URLField(max_length=255, blank=True, verbose_name="Sitio Web")
    
    # Campo extra para el dashboard (slug único para la URL del portal)
    slug = models.SlugField(max_length=100, blank=True)
    
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
        # Generar slug si está presente (siguiendo tu lógica de 'if self.slug')
        if self.slug:
            slug = slugify(self.club_name)
            # Buscamos cuántos clubes tienen ya ese slug (excluyendo el actual)
            same_slug_clubs = Club.objects.filter(slug=slug).exclude(uuid=self.uuid).count()
            
            if same_slug_clubs > 0:
                slug = f'{slug}{same_slug_clubs + 1}'
            
            self.slug = slug
            
        super(Club, self).save(*args, **kwargs)