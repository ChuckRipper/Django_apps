from django.contrib import admin

from .models import Grupa


@admin.register(Grupa)
class GrupaAdmin(admin.ModelAdmin):
    list_display = ("nazwa", "prywatna", "zalozyciel", "utworzono")
    list_filter = ("prywatna",)
