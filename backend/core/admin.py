from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Session, Booking


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_creator', 'oauth_provider', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Ahoum Profile', {'fields': ('is_creator', 'oauth_provider', 'oauth_sub', 'bio', 'avatar_url')}),
    )


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'starts_at', 'capacity', 'location', 'created_at')
    list_filter = ('starts_at', 'creator')
    search_fields = ('title', 'description', 'location', 'creator__email')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'session__title')
