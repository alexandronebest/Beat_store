from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from rest_framework.routers import DefaultRouter
from . import views, views_api

router = DefaultRouter()
router.register(r'songs', views_api.SongViewSet)
router.register(r'genres', views_api.GenreViewSet)

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('music/', views.music_list, name='music_list'),
    path('authors/', views.authors_list, name='authors_list'),
    path('playlist/', views.playlist, name='playlist'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='store/login.html', next_page='store:index'), name='login'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('add_music/', views.add_music, name='add_music'),
    path('edit_music/<int:song_id>/', views.edit_music, name='edit_music'),
    path('delete_music/<int:song_id>/', views.delete_music, name='delete_music'),
    path('like_song/<int:song_id>/', views.like_song, name='like_song'),
    path('play_song/<int:song_id>/', views.play_song, name='play_song'),
    path('cart/add/<int:song_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:song_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart, name='cart'),
    # path('cart_songs/', views.cart_songs, name='cart_songs')
    path('buy_song/<int:song_id>/', views.buy_song, name='buy_song'),
    path('purchase/', views.process_purchase, name='process_purchase'),
    path('top_up_balance/', views.top_up_balance, name='top_up_balance'),
    path('add_to_playlist/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('purchase_contract/<int:purchase_id>/', views.purchase_contract, name='purchase_contract'),
    path('accept_contract/<int:contract_id>/', views.accept_contract, name='accept_contract'),
    path('download_contract/<int:purchase_id>/', views.download_contract_pdf, name='download_contract_pdf'),
    path('logout/', LogoutView.as_view(next_page='store:index'), name='logout'),
    path('api/', include(router.urls)),
]