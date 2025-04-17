from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, F
from django.core.cache import cache
from .models import User, Song, Genre, Profile, Playlist, Transaction
from .forms import SongForm, CustomUserCreationForm, ProfileForm
import json
import logging

logger = logging.getLogger(__name__)

def index(request):
    cache_key = 'index_data'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        # Получаем топ песен и новые песни
        top_songs = Song.objects.annotate(likes_count=Count('likes')).order_by('-likes_count', '-total_plays')[:10]
        new_songs = Song.objects.order_by('-created_at')[:10]
        genres = Genre.objects.all()
        authors = Profile.objects.select_related('user').all()

        # Формируем songs_data только для отображаемых песен (top_songs + new_songs)
        displayed_songs = list(top_songs) + list(new_songs)
        songs_data = [
            {
                'id': song.id,
                'title': song.title,
                'path': song.path.url,  # Используем относительный путь, как в data-song-url
                'author': song.author.username,
                'price': float(song.price),
                'total_likes': song.total_likes,
                'total_plays': song.total_plays
            } for song in displayed_songs
        ]
        songs_json = json.dumps(songs_data)

        # Сохраняем данные в кэш
        cached_data = {
            'top_songs': top_songs,
            'new_songs': new_songs,
            'genres': genres,
            'authors': authors,
            'songs_json': songs_json,
        }
        cache.set(cache_key, cached_data, 300)  # Кэш на 5 минут

    context = cached_data
    return render(request, 'store/index.html', context)

@login_required
def profile(request, username=None):
    user = get_object_or_404(User, username=username) if username else request.user
    profile = user.profile
    songs = Song.objects.filter(author=user).select_related('genre')
    liked_songs = user.liked_songs.select_related('author', 'genre').all()
    playlists = Playlist.objects.filter(user=user)
    purchases = Transaction.objects.filter(buyer=user, is_successful=True).select_related('song')

    if request.method == 'POST' and user == request.user:
        profile.status = request.POST.get('status', '').strip()[:100]
        profile.save(update_fields=['status'])
        messages.success(request, 'Статус успешно обновлён!')
        return redirect('store:profile', username=user.username)

    # Формируем songs_json для плеера
    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays
        } for song in songs
    ]
    songs_json = json.dumps(songs_data)

    context = {
        'profile': profile,
        'songs': songs,
        'liked_songs': liked_songs,
        'playlists': playlists,
        'purchases': purchases,
        'songs_json': songs_json,
    }
    return render(request, 'store/profile.html', context)

@login_required
def music_list_view(request):
    genres = Genre.objects.all()
    authors = Profile.objects.select_related('user').all()
    songs = Song.objects.select_related('author', 'genre').all()

    if genre_id := request.GET.get('genre'):
        songs = songs.filter(genre__id=genre_id)
    if author_id := request.GET.get('author'):
        songs = songs.filter(author__id=author_id)
    if title := request.GET.get('query'):
        songs = songs.filter(title__icontains=title.strip())

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays
        } for song in songs
    ]
    songs_json = json.dumps(songs_data)

    context = {
        'songs': songs,
        'genres': genres,
        'authors': authors,
        'songs_json': songs_json,
    }
    return render(request, 'store/music_list.html', context)

@login_required
def add_music_view(request):
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.author = request.user
            song.save()
            cache.delete('index_data')  # Очистка кэша при добавлении
            messages.success(request, 'Песня успешно добавлена!')
            return redirect('store:music_list')
        messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = SongForm()
    return render(request, 'store/add_music.html', {'form': form})

@login_required
def edit_music_view(request, song_id):
    song = get_object_or_404(Song, id=song_id, author=request.user)
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES, instance=song)
        if form.is_valid():
            form.save()
            cache.delete('index_data')
            messages.success(request, 'Песня успешно обновлена!')
            return redirect('store:music_list')
        messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = SongForm(instance=song)
    return render(request, 'store/edit_music.html', {'form': form, 'song': song})

@login_required
def delete_music_view(request, song_id):
    song = get_object_or_404(Song, id=song_id, author=request.user)
    if request.method == 'POST':
        song.delete()
        cache.delete('index_data')
        messages.success(request, 'Песня успешно удалена!')
        return redirect('store:music_list')
    return render(request, 'store/delete_music.html', {'song': song})

def search_view(request):
    query = request.GET.get('query', '').strip()
    songs = Song.objects.filter(title__icontains=query).select_related('author', 'genre') if query else Song.objects.none()
    
    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays
        } for song in songs
    ]
    songs_json = json.dumps(songs_data)

    return render(request, 'store/search_results.html', {
        'songs': songs,
        'query': query,
        'songs_json': songs_json,
    })

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'store/register.html'
    success_url = reverse_lazy('store:index')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, 'Регистрация прошла успешно!')
        return super().form_valid(form)

@login_required
def upload_photo(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Фото успешно обновлено!')
            return redirect('store:profile', username=request.user.username)
        messages.error(request, 'Исправьте ошибки в форме.')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'store/upload_photo.html', {'form': form})

@login_required
def authors_list_view(request):
    authors = Profile.objects.select_related('user').all()
    return render(request, 'store/profiles.html', {'profiles': authors})

@login_required
@require_POST
@csrf_protect
def like_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user
        liked = song.likes.filter(id=user.id).exists()

        if liked:
            song.likes.remove(user)
            logger.debug(f"User {user.username} unliked song {song_id}")
        else:
            song.likes.add(user)
            logger.debug(f"User {user.username} liked song {song_id}")

        total_likes = song.likes.count()
        cache.delete('index_data')
        return JsonResponse({
            'liked': not liked,
            'total_likes': total_likes,
        }, status=200)
    except Exception as e:
        logger.error(f"Error in like_song: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
@require_POST
@csrf_protect
def play_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        song.total_plays = F('total_plays') + 1
        song.save(update_fields=['total_plays'])
        song.refresh_from_db(fields=['total_plays'])
        logger.debug(f"Song {song_id} played by {request.user.username}, total_plays: {song.total_plays}")
        cache.delete('index_data')
        return JsonResponse({'total_plays': song.total_plays}, status=200)
    except Exception as e:
        logger.error(f"Error in play_song: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
def buy_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    user = request.user

    # Проверка, куплена ли песня
    if Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
        messages.info(request, f'Песня "{song.title}" уже куплена!')
        return redirect('store:music_list')

    if request.method == 'POST':
        if user.balance >= song.price:
            # Создаём транзакцию
            transaction = Transaction.objects.create(
                buyer=user,
                song=song,
                amount=song.price,
                is_successful=True
            )
            # Обновляем баланс покупателя и автора
            user.balance -= song.price
            song.author.balance += song.price
            user.save(update_fields=['balance'])
            song.author.save(update_fields=['balance'])
            messages.success(request, f'Песня "{song.title}" успешно куплена за ₽{song.price}!')
            cache.delete('index_data')
            return redirect('store:profile', username=user.username)
        else:
            messages.error(request, 'Недостаточно средств на балансе!')
            return redirect('store:buy_song', song_id=song_id)

    context = {
        'song': song,
        'user_balance': user.balance,
    }
    return render(request, 'store/buy_song.html', context)

@login_required
def add_to_playlist(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    playlist, created = Playlist.objects.get_or_create(user=request.user)
    playlist.songs.add(song)
    messages.success(request, f'Песня "{song.title}" добавлена в плейлист!')
    return redirect('store:playlist')

@login_required
def playlist_view(request):
    playlist = Playlist.objects.filter(user=request.user).first()
    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays
        } for song in playlist.songs.all()
    ] if playlist else []
    songs_json = json.dumps(songs_data)
    
    context = {
        'playlist': playlist,
        'songs_json': songs_json,
    }
    return render(request, 'store/playlist.html', context)