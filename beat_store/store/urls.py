from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'store'

urlpatterns = [
    # Главная страница и списки
    path('', views.index, name='index'),
    path('music/', views.music_list, name='music_list'),
    path('authors/', views.authors_list, name='authors_list'),
    path('playlist/', views.playlist, name='playlist'),
    
    # Аутентификация
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='store:index'), name='logout'),
    
    # Профиль
    path('profile/<str:username>/', views.profile, name='profile'),
    
    # Управление музыкой
    path('music/add/', views.add_music, name='add_music'),
    path('music/edit/<int:song_id>/', views.edit_music, name='edit_music'),
    path('music/delete/<int:song_id>/', views.delete_music, name='delete_music'),
    path('upload_song/', views.upload_song, name='upload_song'),
    
    # Действия с песнями
    path('like/<int:song_id>/', views.like_song, name='like_song'),
    path('play/<int:song_id>/', views.play_song, name='play_song'),
    
    # Корзина и покупки
    path('cart/add/<int:song_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:song_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart, name='cart'),
    path('buy/<int:song_id>/', views.buy_song, name='buy_song'),
    path('purchase/', views.process_purchase, name='process_purchase'),
    path('purchase/<int:purchase_id>/contract/', views.purchase_contract, name='purchase_contract'),
    
    # Пополнение баланса
    path('top-up/', views.top_up_balance, name='top_up_balance'),
    
    # Добавление в плейлист
    # path('playlist/add/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
]