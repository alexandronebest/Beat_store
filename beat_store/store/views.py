from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as BaseLoginView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, F
from django.core.paginator import Paginator
from .models import User, Song, Genre, Profile, Playlist, Transaction
from .forms import SongForm, CustomUserCreationForm, ProfileForm
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class CustomLoginView(BaseLoginView):
    template_name = 'store/login.html'
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        logger.info(f"Пользователь {user.username} успешно вошел в систему")
        messages.success(self.request, f"Добро пожаловать, {user.username}!")
        next_url = self.request.POST.get('next', self.request.GET.get('next', reverse_lazy('store:index')))
        return redirect(next_url)

    def form_invalid(self, form):
        logger.warning(f"Неудачная попытка входа: {form.errors}")
        messages.error(self.request, "Неверное имя пользователя или пароль.")
        return super().form_invalid(form)

def index(request):
    top_songs = Song.objects.select_related('author', 'genre').prefetch_related('likes').annotate(
        likes_count=Count('likes')
    ).order_by('-total_plays')[:10]

    new_songs = Song.objects.select_related('author', 'genre').prefetch_related('likes').annotate(
        likes_count=Count('likes')
    ).order_by('-created_at')[:10]

    genres = Genre.objects.all()
    authors = Profile.objects.select_related('user').all()

    all_songs = list(top_songs) + list(new_songs)
    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in all_songs
    ]
    songs_json = json.dumps(songs_data)

    logger.debug('Топ песен: %s', [{'id': song.id, 'title': song.title} for song in top_songs])
    logger.debug('Новые песни: %s', [{'id': song.id, 'title': song.title} for song in new_songs])
    logger.debug('Данные для плеера: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

    context = {
        'top_songs': top_songs,
        'new_songs': new_songs,
        'genres': genres,
        'authors': authors,
        'songs_json': songs_json,
        'no_songs_message': 'Нет песен' if not all_songs else None,
    }
    return render(request, 'store/index.html', context)

@login_required
def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Вы успешно вышли из аккаунта!')
        logger.info(f"Пользователь {request.user.username} вышел из системы")
        return redirect('store:index')
    return HttpResponse(status=405)

@login_required
def profile(request, username=None):
    user = get_object_or_404(User, username=username) if username else request.user
    profile = user.profile
    songs = Song.objects.filter(author=user).select_related('genre').prefetch_related('likes')
    liked_songs = user.liked_songs.select_related('author', 'genre').all()
    playlists = Playlist.objects.filter(user=user).prefetch_related('songs')
    purchases = Transaction.objects.filter(buyer=user, is_successful=True).select_related('song')

    if request.method == 'POST' and user == request.user:
        profile.status = request.POST.get('status', '').strip()[:100]
        profile.save(update_fields=['status'])
        messages.success(request, 'Статус успешно обновлен!')
        return redirect('store:profile', username=user.username)

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in songs
    ]
    songs_json = json.dumps(songs_data)
    logger.debug('Данные песен в профиле: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

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
    songs = Song.objects.select_related('author', 'genre').prefetch_related('likes')

    if genre_id := request.GET.get('genre'):
        songs = songs.filter(genre__id=genre_id)
    if author_id := request.GET.get('author'):
        songs = songs.filter(author__id=author_id)
    if title := request.GET.get('query'):
        songs = songs.filter(title__icontains=title.strip())

    paginator = Paginator(songs, 20)
    page_number = request.GET.get('page', 1)
    songs_page = paginator.get_page(page_number)

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in songs_page
    ]
    songs_json = json.dumps(songs_data)
    logger.debug('Данные песен в списке музыки: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

    context = {
        'songs': songs_page,
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
        messages.success(request, 'Песня успешно удалена!')
        return redirect('store:music_list')
    return render(request, 'store/delete_music.html', {'song': song})

def search_view(request):
    query = request.GET.get('query', '').strip()
    songs = Song.objects.filter(title__icontains=query).select_related('author', 'genre').prefetch_related('likes') if query else Song.objects.none()

    paginator = Paginator(songs, 20)
    page_number = request.GET.get('page', 1)
    songs_page = paginator.get_page(page_number)

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in songs_page
    ]
    songs_json = json.dumps(songs_data)
    logger.debug('Результаты поиска песен: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

    return render(request, 'store/search_results.html', {
        'songs': songs_page,
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
        logger.info(f"Пользователь {user.username} успешно зарегистрировался")
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(f"Неудачная попытка регистрации: {form.errors}")
        messages.error(self.request, "Исправьте ошибки в форме.")
        return super().form_invalid(form)

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
            logger.debug(f"Пользователь {user.username} убрал лайк с песни {song_id}")
        else:
            song.likes.add(user)
            logger.debug(f"Пользователь {user.username} поставил лайк на песню {song_id}")

        total_likes = song.likes.count()
        return JsonResponse({
            'liked': not liked,
            'total_likes': total_likes,
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в like_song: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@login_required
@require_POST
@csrf_protect
def play_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        song.total_plays = F('total_plays') + 1
        song.save(update_fields=['total_plays'])
        song.refresh_from_db(fields=['total_plays'])
        logger.debug(f"Песня {song_id} воспроизведена пользователем {request.user.username}, всего воспроизведений: {song.total_plays}")
        return JsonResponse({'total_plays': song.total_plays}, status=200)
    except Exception as e:
        logger.error(f"Ошибка в play_song: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@login_required
@require_POST
@csrf_protect
def buy_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user

        if Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
            messages.info(request, f'Песня "{song.title}" уже куплена!')
            return redirect('store:cart')

        if user.balance >= song.price:
            Transaction.objects.create(
                buyer=user,
                song=song,
                amount=song.price,
                is_successful=True
            )
            user.balance -= song.price
            song.author.balance += song.price
            user.save(update_fields=['balance'])
            song.author.save(update_fields=['balance'])

            cart = request.session.get('cart', [])
            if song_id in cart:
                cart.remove(song_id)
                request.session['cart'] = cart
                request.session.modified = True

            logger.info(f"Пользователь {user.username} купил песню {song_id} за {song.price}")
            messages.success(request, f'Песня "{song.title}" успешно куплена!')
            return redirect('store:cart')
        else:
            logger.warning(f"У пользователя {user.username} недостаточно средств для покупки песни {song_id}")
            messages.error(request, 'Недостаточно средств на балансе!')
            return redirect('store:cart')
    except Exception as e:
        logger.error(f"Ошибка в buy_song: {str(e)}")
        messages.error(request, 'Произошла ошибка при покупке.')
        return redirect('store:cart')

@login_required
def top_up_balance(request):
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            if amount <= 0:
                messages.error(request, 'Сумма должна быть больше нуля!')
                return redirect('store:top_up_balance')
            
            user = request.user
            user.balance += amount
            user.save(update_fields=['balance'])
            logger.info(f"Пользователь {user.username} пополнил баланс на {amount}")
            messages.success(request, f'Баланс успешно пополнен на ₽{amount}!')
            return redirect('store:profile', username=user.username)
        except (ValueError, TypeError):
            messages.error(request, 'Неверный формат суммы!')
            return redirect('store:top_up_balance')
    return render(request, 'store/top_up_balance.html')

@login_required
def add_to_playlist(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    playlist, created = Playlist.objects.get_or_create(user=request.user)
    if song not in playlist.songs.all():
        playlist.songs.add(song)
        messages.success(request, f'Песня "{song.title}" добавлена в плейлист!')
        logger.debug(f"Пользователь {request.user.username} добавил песню {song_id} в плейлист")
    else:
        messages.info(request, f'Песня "{song.title}" уже в плейлисте!')
    return redirect('store:playlist')

@login_required
def playlist_view(request):
    playlist = Playlist.objects.filter(user=request.user).prefetch_related('songs').first()
    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in playlist.songs.all()
    ] if playlist else []
    songs_json = json.dumps(songs_data)
    logger.debug('Данные песен в плейлисте: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

    context = {
        'playlist': playlist,
        'songs_json': songs_json,
    }
    return render(request, 'store/playlist.html', context)

@login_required
@require_POST
@csrf_protect
def remove_from_playlist(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        playlist = Playlist.objects.filter(user=request.user).first()
        if playlist and song in playlist.songs.all():
            playlist.songs.remove(song)
            logger.debug(f"Пользователь {request.user.username} убрал песню {song_id} из плейлиста")
            messages.success(request, f'Песня "{song.title}" удалена из плейлиста!')
        else:
            logger.warning(f"Песня {song_id} не найдена в плейлисте пользователя {request.user.username}")
            messages.error(request, f'Песня "{song.title}" не найдена в вашем плейлисте!')
        return redirect('store:playlist')
    except Exception as e:
        logger.error(f"Ошибка в remove_from_playlist: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@login_required
def cart_view(request):
    cart = request.session.get('cart', [])
    songs = Song.objects.filter(id__in=cart).select_related('author', 'genre').prefetch_related('likes')
    total_price = sum(song.price for song in songs)

    songs_data = [
        {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        } for song in songs
    ]
    songs_json = json.dumps(songs_data)
    logger.debug('Данные песен в корзине: %s', [{'id': song['id'], 'title': song['title']} for song in songs_data])

    context = {
        'songs': songs,
        'total_price': total_price,
        'songs_json': songs_json,
        'profile': request.user.profile,
    }
    return render(request, 'store/cart.html', context)

@login_required
@require_POST
@csrf_protect
def add_to_cart(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user

        if Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
            logger.debug(f"Песня {song_id} уже куплена пользователем {user.username}")
            return JsonResponse({
                'success': False,
                'message': f'Песня "{song.title}" уже куплена!',
                'is_purchased': True
            }, status=200)

        cart = request.session.get('cart', [])
        if song_id not in cart:
            cart.append(song_id)
            request.session['cart'] = cart
            request.session.modified = True
            logger.debug(f"Пользователь {user.username} добавил песню {song_id} в корзину")
            return JsonResponse({
                'success': True,
                'message': f'Песня "{song.title}" добавлена в корзину!',
                'in_cart': True
            }, status=200)
        else:
            logger.debug(f"Песня {song_id} уже в корзине пользователя {user.username}")
            return JsonResponse({
                'success': False,
                'message': f'Песня "{song.title}" уже в корзине!',
                'in_cart': True
            }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в add_to_cart: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@login_required
def cart_status(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user
        cart = request.session.get('cart', [])
        in_cart = song_id in cart
        is_purchased = Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists()
        logger.debug(f"Статус корзины для песни {song_id}: in_cart={in_cart}, is_purchased={is_purchased}")
        return JsonResponse({
            'in_cart': in_cart,
            'is_purchased': is_purchased
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в cart_status: {str(e)}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@login_required
def remove_from_cart(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    cart = request.session.get('cart', [])
    if song_id in cart:
        cart.remove(song_id)
        request.session['cart'] = cart
        request.session.modified = True
        logger.debug(f"Пользователь {request.user.username} убрал песню {song_id} из корзины")
        messages.success(request, f'Песня "{song.title}" удалена из корзины!')
    else:
        logger.debug(f"Песня {song_id} не была в корзине пользователя {request.user.username}")
        messages.info(request, f'Песня "{song.title}" не была в корзине!')
    return redirect('store:cart')

@login_required
def get_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        song_data = {
            'id': song.id,
            'title': song.title,
            'path': request.build_absolute_uri(song.path.url),
            'author': song.author.username,
            'price': float(song.price),
            'total_likes': song.total_likes,
            'total_plays': song.total_plays,
            'image': request.build_absolute_uri(song.cover.url) if song.cover else None,
        }
        logger.debug(f"Получены данные песни {song_id}: %s", song_data)
        return JsonResponse(song_data, status=200)
    except Exception as e:
        logger.error(f"Ошибка в get_song: {str(e)}")
        return JsonResponse({'error': 'Песня не найдена'}, status=404)