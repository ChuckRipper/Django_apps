from django.contrib import admin

from .models import AkcjaModeratora, Zgloszenie


@admin.register(Zgloszenie)
class ZgloszenieAdmin(admin.ModelAdmin):
    list_display = ("typ", "powod", "status", "utworzono")
    list_filter = ("status", "typ")
    exclude = ("kopia_tresci",)


@admin.register(AkcjaModeratora)
class AkcjaModeratoraAdmin(admin.ModelAdmin):
    """Historia tylko do odczytu – nikt jej nie poprawia."""

    list_display = ("utworzono", "wykonal", "akcja", "cel")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
