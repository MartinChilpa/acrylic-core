from django.contrib import admin
from .models import Club, Player

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    # Campos que se muestran en la lista (clonando el estilo de Artist)
    list_display = ['club_name', 'stadium_name', 'user', 'is_active', 'portal_web']
    
    # Buscador potente para encontrar clubes rápido
    search_fields = ['club_name', 'stadium_name', 'user__email']
    
    # Filtros laterales
    list_filter = ['is_active']
    
    # Para que el selector de usuario sea por ID/Buscador y no un desplegable pesado
    raw_id_fields = ['user']

    # IMPORTANTE: Aquí definimos qué campos aparecen en el formulario de "Add Club"
    fields = [
        'user',
        'club_name',
        'slug',
        'stadium_name',
        'portal_web',
        'team_name',
        'tagline',
        'colors',
        'auth_promo',
        'sidenav',
        'is_active',
    ]


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "club", "nationality", "is_active"]
    search_fields = ["name", "club__club_name"]
    list_filter = ["club", "nationality", "is_active"]
    raw_id_fields = ["club"]
