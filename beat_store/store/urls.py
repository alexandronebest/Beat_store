from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('music/', views.music_list_view, name='music_list'),
    path('add-music/', views.add_music_view, name='add_music'),
    path('edit-music/<int:song_id>/', views.edit_music_view, name='edit_music'),
    path('delete-music/<int:song_id>/', views.delete_music_view, name='delete_music'),
    path('search/', views.search_view, name='search_results'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('upload-photo/', views.upload_photo, name='upload_photo'),
    path('authors/', views.authors_list_view, name='authors_list'),
    path('like/<int:song_id>/', views.like_song, name='like_song'),
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('buy/<int:song_id>/', views.buy_song, name='buy_song'),
    path('playlist/add/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('playlist/', views.playlist_view, name='playlist'),
    path('accounts/login/', LoginView.as_view(
        template_name='store/login.html',
        redirect_authenticated_user=True,
        extra_context={'next': 'store:index'}
    ), name='login'),
    path('accounts/logout/', LogoutView.as_view(
        template_name='store/logout.html',
        next_page='store:index'
    ), name='logout'),
]