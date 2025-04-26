from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('music/', views.music_list, name='music_list'),
    path('authors/', views.authors_list, name='authors_list'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('upload/', views.upload_song, name='upload_song'),
    path('like/<int:song_id>/', views.like_song, name='like_song'),
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('cart/add/<int:song_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/remove/<int:song_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('buy/<int:song_id>/', views.buy_song, name='buy_song'),
    path('purchase/', views.process_purchase, name='process_purchase'),
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),  # Добавлен маршрут для регистрации
    path('playlist/', views.playlist, name='playlist'),  # Добавлен маршрут для плейлиста
]