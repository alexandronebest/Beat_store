from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Genre, Song, Profile, Playlist, Transaction, Purchase, Cart

# Кастомная админ-панель для User
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'balance', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('username', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'balance')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'balance', 'is_staff', 'is_active')}
        ),
    )

# Админ-панель для Genre
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

# Админ-панель для Song
@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'price', 'total_plays', 'total_likes', 'created_at')
    list_filter = ('genre', 'author', 'created_at')
    search_fields = ('title', 'author__username')
    date_hierarchy = 'created_at'
    list_editable = ('price',)
    raw_id_fields = ('author', 'genre')  # Для удобства работы с большими списками
    filter_horizontal = ('likes',)  # Удобный интерфейс для ManyToMany

# Админ-панель для Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'total_likes', 'total_plays')
    search_fields = ('user__username', 'status')
    list_filter = ('status',)
    raw_id_fields = ('user',)

# Админ-панель для Playlist
@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'song_count')
    search_fields = ('user__username',)
    list_filter = ('created_at',)
    filter_horizontal = ('songs',)
    raw_id_fields = ('user',)

    def song_count(self, obj):
        return obj.songs.count()
    song_count.short_description = 'Количество песен'

# Админ-панель для Transaction
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'song', 'amount', 'created_at', 'is_successful')
    list_filter = ('is_successful', 'created_at')
    search_fields = ('buyer__username', 'song__title')
    date_hierarchy = 'created_at'
    raw_id_fields = ('buyer', 'song')

# Админ-панель для Purchase
@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_price', 'purchase_date', 'song_count')
    list_filter = ('purchase_date',)
    search_fields = ('user__username',)
    date_hierarchy = 'purchase_date'
    filter_horizontal = ('songs',)
    raw_id_fields = ('user',)

    def song_count(self, obj):
        return obj.songs.count()
    song_count.short_description = 'Количество песен'

# Админ-панель для Cart
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'song_count')
    search_fields = ('user__username',)
    filter_horizontal = ('songs',)
    raw_id_fields = ('user',)

    def song_count(self, obj):
        return obj.songs.count()
    song_count.short_description = 'Количество песен'

# Регистрация модели User
admin.site.register(User, CustomUserAdmin)