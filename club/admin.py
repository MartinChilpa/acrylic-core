from django.contrib import admin
from .models import Club

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
    # Quitamos 'slug' de aquí para que NO aparezca al llenar los datos
    fields = ['user', 'club_name', 'stadium_name', 'portal_web', 'is_active']