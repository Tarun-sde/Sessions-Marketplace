from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_creator', 'oauth_provider', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Ahoum Profile', {'fields': ('is_creator', 'oauth_provider', 'oauth_sub', 'bio', 'avatar_url')}),
    )
