import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, F
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django import forms
from .models import Song, Genre, Transaction, Profile, User
from .forms import SongForm, ProfileForm, CustomUserCreationForm
import json

logger = logging.getLogger(__name__)

# Форма для пополнения баланса
class TopUpBalanceForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        label='Сумма пополнения',
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'})
    )

# Кастомный логин
class CustomLoginView(LoginView):
    template_name = 'store/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('store:index')

    def form_invalid(self, form):
        messages.error(self.request, 'Неверное имя пользователя или пароль.')
        return super().form_invalid(form)

# Главная страница
def index(request):
    top_songs = Song.objects.annotate(like_count=Count('likes')).order_by('-like_count', '-total_plays')[:10]
    new_songs = Song.objects.order_by('-created_at')[:10]
    genres = Genre.objects.all()

    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
        for song in (list(top_songs) + list(new_songs))
    ]

    context = {
        'top_songs': top_songs,
        'new_songs': new_songs,
        'genres': genres,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/index.html', context)

# Список музыки
def music_list(request):
    songs = Song.objects.all().order_by('-created_at')
    genres = Genre.objects.all()

    genre_id = request.GET.get('genre')
    search_query = request.GET.get('search')

    if genre_id:
        songs = songs.filter(genre_id=genre_id)
    if search_query:
        songs = songs.filter(title__icontains=search_query) | songs.filter(author__username__icontains=search_query)

    paginator = Paginator(songs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
        for song in songs
    ]

    context = {
        'page_obj': page_obj,
        'genres': genres,
        'selected_genre': genre_id,
        'search_query': search_query,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/music_list.html', context)

# Список авторов
# def authors_list(request):
#     authors = User.objects.filter(song__isnull=False).distinct().order_by('username')
#     paginator = Paginator(authors, 12)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     context = {
#         'page_obj': page_obj,
#     }
#     return render(request, 'store/authors_list.html', context)
def authors_list(request):
    # Фильтруем пользователей, у которых есть песни
    authors = User.objects.filter(songs__isnull=False).distinct().order_by('username')
    # Получаем связанные профили
    profiles = Profile.objects.filter(user__in=authors).select_related('user')
    # Пагинация
    paginator = Paginator(profiles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'store/profiles.html', context)

# Плейлист пользователя
@login_required
def playlist(request):
    songs = Song.objects.filter(transaction__buyer=request.user, transaction__is_successful=True).order_by('-created_at')
    paginator = Paginator(songs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
        for song in songs
    ]

    context = {
        'page_obj': page_obj,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/playlist.html', context)

# Регистрация
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Profile.objects.get_or_create(user=user)  # Создаём профиль при регистрации
            messages.success(request, 'Регистрация успешна!')
            return redirect('store:index')
        else:
            messages.error(request, 'Ошибка при регистрации. Проверьте введенные данные.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})

# Профиль пользователя
@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = get_object_or_404(Profile, user=user)
    is_own_profile = request.user.username == username
    songs = Song.objects.filter(author=user).order_by('-created_at')
    liked_songs = Song.objects.filter(likes=user).order_by('-created_at')

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('store:profile', username=username)
        else:
            messages.error(request, 'Ошибка при обновлении профиля. Проверьте данные.')
    else:
        form = ProfileForm(instance=profile)

    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
        for song in (list(songs) + list(liked_songs))
    ]

    context = {
        'profile': profile,
        'is_own_profile': is_own_profile,
        'songs': songs,
        'liked_songs': liked_songs,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
        'form': form,
    }
    logger.debug(f"Profile view: username={username}, songs={songs.count()}, liked_songs={liked_songs.count()}")
    return render(request, 'store/profile.html', context)

# Загрузка песни
@login_required
def upload_song(request):
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.author = request.user
            song.save()
            messages.success(request, 'Песня успешно загружена!')
            return redirect('store:profile', username=request.user.username)
        else:
            messages.error(request, 'Ошибка при загрузке песни. Проверьте введенные данные.')
    else:
        form = SongForm()
    return render(request, 'store/upload_song.html', {'form': form})

# Добавление песни
@login_required
def add_music(request):
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.author = request.user
            song.save()
            messages.success(request, 'Песня успешно добавлена.')
            return redirect('store:profile', username=request.user.username)
        else:
            messages.error(request, 'Ошибка при добавлении песни. Проверьте данные.')
    else:
        form = SongForm()
    return render(request, 'store/add_music.html', {'form': form})

# Редактирование песни
@login_required
def edit_music(request, song_id):
    song = get_object_or_404(Song, id=song_id, author=request.user)
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES, instance=song)
        if form.is_valid():
            form.save()
            messages.success(request, 'Песня успешно отредактирована.')
            return redirect('store:profile', username=request.user.username)
        else:
            messages.error(request, 'Ошибка при редактировании песни. Проверьте данные.')
    else:
        form = SongForm(instance=song)
    return render(request, 'store/edit_music.html', {'form': form, 'song': song})

# Удаление песни
@login_required
def delete_music(request, song_id):
    song = get_object_or_404(Song, id=song_id, author=request.user)
    if request.method == 'POST':
        song.delete()
        messages.success(request, 'Песня успешно удалена.')
        return redirect('store:profile', username=request.user.username)
    return redirect('store:profile', username=request.user.username)

# Лайк песни
@login_required
@require_POST
@csrf_protect
def like_song(request, song_id):
    logger.debug(f"Получен запрос на лайк для song_id {song_id} от пользователя {request.user.username}")
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user

        if not user.is_authenticated:
            logger.warning(f"Неавторизованный пользователь пытался поставить лайк на песню {song_id}")
            return JsonResponse({
                'success': False,
                'message': 'Пожалуйста, войдите в аккаунт.',
            }, status=403)

        if user in song.likes.all():
            song.likes.remove(user)
            liked = False
            logger.debug(f"Пользователь {user.username} убрал лайк с песни {song_id}")
        else:
            song.likes.add(user)
            liked = True
            logger.debug(f"Пользователь {user.username} поставил лайк на песню {song_id}")

        song.save()

        return JsonResponse({
            'success': True,
            'liked': liked,
            'total_likes': song.total_likes,
            'message': 'Лайк успешно обновлён'
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в like_song для song_id {song_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при обработке лайка: {str(e)}',
            'error': str(e)
        }, status=403 if 'permission' in str(e).lower() else 500)

# Воспроизведение песни
@login_required
@require_POST
@csrf_protect
def play_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        song.total_plays = F('total_plays') + 1
        song.save()
        song.refresh_from_db()

        logger.debug(f"Песня {song_id} воспроизведена, общее количество: {song.total_plays}")
        return JsonResponse({
            'success': True,
            'total_plays': song.total_plays,
            'message': 'Счётчик воспроизведений обновлён'
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в play_song для song_id {song_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при увеличении счётчика воспроизведений: {str(e)}',
            'error': str(e)
        }, status=500)

# Добавление в корзину
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
                'message': f'Песня "{song.title}" уже куплена',
                'is_purchased': True
            }, status=200)

        if 'cart' not in request.session:
            request.session['cart'] = []

        cart = request.session['cart']
        if song_id not in cart:
            cart.append(song_id)
            request.session['cart'] = cart
            request.session.modified = True
            logger.debug(f"Пользователь {user.username} добавил песню {song_id} в корзину")
            return JsonResponse({
                'success': True,
                'message': f'Песня "{song.title}" добавлена в корзину',
                'in_cart': True
            }, status=200)
        else:
            logger.debug(f"Песня {song_id} уже в корзине пользователя {user.username}")
            return JsonResponse({
                'success': False,
                'message': f'Песня "{song.title}" уже в корзине',
                'in_cart': True
            }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в add_to_cart для song_id {song_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при добавлении в корзину: {str(e)}',
            'error': str(e)
        }, status=403 if 'permission' in str(e).lower() else 500)

# Корзина
@login_required
def cart(request):
    cart = request.session.get('cart', [])
    songs = Song.objects.filter(id__in=cart)
    
    total_price = sum(song.price for song in songs)
    
    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
        for song in songs
    ]

    context = {
        'songs': songs,
        'total_price': total_price,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/cart.html', context)

# Удаление из корзины
@login_required
@require_POST
@csrf_protect
def remove_from_cart(request, song_id):
    try:
        cart = request.session.get('cart', [])
        if song_id in cart:
            cart.remove(song_id)
            request.session['cart'] = cart
            request.session.modified = True
            logger.debug(f"Песня {song_id} удалена из корзины пользователя {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'Песня удалена из корзины'
            }, status=200)
        else:
            logger.debug(f"Песня {song_id} не найдена в корзине пользователя {request.user.username}")
            return JsonResponse({
                'success': False,
                'message': 'Песня не найдена в корзине'
            }, status=400)
    except Exception as e:
        logger.error(f"Ошибка в remove_from_cart для song_id {song_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при удалении из корзины: {str(e)}',
            'error': str(e)
        }, status=500)

# Покупка одной песни
@login_required
def buy_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    user = request.user

    if Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
        messages.error(request, 'Вы уже приобрели эту песню.')
        return redirect('store:cart')

    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays
        }
    ]

    context = {
        'song': song,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/buy_song.html', context)

# Обработка покупки
@login_required
@require_POST
@csrf_protect
def process_purchase(request):
    try:
        cart = request.session.get('cart', [])
        if not cart:
            logger.debug(f"Корзина пуста при попытке покупки пользователем {request.user.username}")
            return JsonResponse({
                'success': False,
                'message': 'Корзина пуста'
            }, status=400)

        songs = Song.objects.filter(id__in=cart)
        user = request.user

        for song in songs:
            if not Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
                Transaction.objects.create(
                    buyer=user,
                    song=song,
                    amount=song.price,
                    is_successful=True
                )
                logger.debug(f"Успешная покупка песни {song.id} пользователем {user.username}")

        request.session['cart'] = []
        request.session.modified = True
        logger.debug(f"Корзина очищена после покупки для пользователя {request.user.username}")
        return JsonResponse({
            'success': True,
            'message': 'Покупка успешно завершена'
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в process_purchase для пользователя {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при обработке покупки: {str(e)}',
            'error': str(e)
        }, status=500)

# Пополнение баланса
@login_required
def top_up_balance(request):
    if request.method == 'POST':
        form = TopUpBalanceForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            user = request.user
            user.balance += amount
            user.save()
            messages.success(request, f'Баланс успешно пополнен на ₽{amount}.')
            logger.debug(f"Пользователь {request.user.username} пополнил баланс на {amount}")
            return redirect('store:cart')
        else:
            messages.error(request, 'Ошибка в форме пополнения. Проверьте введённые данные.')
    else:
        form = TopUpBalanceForm()
    
    context = {
        'form': form,
        'current_balance': request.user.balance,
    }
    return render(request, 'store/top_up_balance.html', context)