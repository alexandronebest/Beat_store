from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.CustomLoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('music/', views.music_list_view, name='music_list'),
    path('add_music/', views.add_music_view, name='add_music'),
    path('edit_music/<int:song_id>/', views.edit_music_view, name='edit_music'),
    path('delete_music/<int:song_id>/', views.delete_music_view, name='delete_music'),
    path('search/', views.search_view, name='search'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('upload_photo/', views.upload_photo, name='upload_photo'),
    path('authors/', views.authors_list_view, name='authors_list'),
    path('like/<int:song_id>/', views.like_song, name='like_song'),
    path('play/<int:song_id>/', views.play_song, name='play_song'),
    path('buy/<int:song_id>/', views.buy_song, name='buy_song'),
    path('top-up-balance/', views.top_up_balance, name='top_up_balance'),
    path('playlist/add/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('playlist/', views.playlist_view, name='playlist'),
    path('playlist/remove/<int:song_id>/', views.remove_from_playlist, name='remove_from_playlist'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:song_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/status/<int:song_id>/', views.cart_status, name='cart_status'),
    path('cart/remove/<int:song_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('song/<int:song_id>/', views.get_song, name='get_song'),
]