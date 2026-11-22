from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Uzytkownik


@admin.register(Uzytkownik)
class UzytkownikAdmin(UserAdmin):
    list_display = ("username", "rola", "is_active", "zablokowany_do", "is_staff")
    list_filter = ("rola", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Portal", {"fields": ("rola", "zablokowany_do")}),)
