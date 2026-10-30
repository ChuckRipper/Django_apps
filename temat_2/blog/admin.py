# blog/admin.py - rejestracja modelu w panelu admina
from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'created_at')
    search_fields = ('name', 'description', 'author')
    prepopulated_fields = {'slug': ('name',)}
