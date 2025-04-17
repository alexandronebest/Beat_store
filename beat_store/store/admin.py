from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Genre, Song, Profile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'price', 'total_plays', 'created_at')  # Добавляем total_plays
    list_filter = ('genre', 'author')
    search_fields = ('title', 'author__username')
    date_hierarchy = 'created_at'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status')
    search_fields = ('user__username', 'status')