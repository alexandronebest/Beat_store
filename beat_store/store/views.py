import logging
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, F
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.db import transaction
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import User, Song, Genre, Transaction, Profile, Cart, Purchase, Playlist, Contract
from .forms import SongForm, ProfileForm, CustomUserCreationForm
from django import forms  # Импорт для формы

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

    songs = list(top_songs) + list(new_songs)
    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
        for song in songs
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
    songs = Song.objects.select_related('author', 'genre').all()
    genres = Genre.objects.all()
    authors = Profile.objects.filter(user__songs__isnull=False).select_related('user').distinct()

    genre_id = request.GET.get('genre')
    search_query = request.GET.get('search')
    author_id = request.GET.get('author')

    if genre_id:
        songs = songs.filter(genre_id=genre_id)
    if search_query:
        songs = songs.filter(title__icontains=search_query) | songs.filter(author__username__icontains=search_query)
    if author_id:
        songs = songs.filter(author_id=author_id)

    songs = songs.order_by('-created_at')
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
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
        for song in page_obj
    ]

    context = {
        'page_obj': page_obj,
        'genres': genres,
        'authors': authors,
        'selected_genre': genre_id,
        'selected_author': author_id,
        'search_query': search_query,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/music_list.html', context)

# Список авторов
def authors_list(request):
    profiles = Profile.objects.filter(user__songs__isnull=False).select_related('user').order_by('user__username')
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
    playlist = get_object_or_404(Playlist, user=request.user)
    songs = playlist.songs.select_related('author').order_by('-created_at')
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
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
        for song in page_obj
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
            Profile.objects.get_or_create(user=user)
            Cart.objects.get_or_create(user=user)
            Playlist.objects.get_or_create(user=user)
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
    is_own_profile = request.user == user
    
    # Получаем песни без сортировки
    songs = Song.objects.filter(author=user).select_related('genre')
    liked_songs = Song.objects.filter(likes=user).select_related('genre')
    
    # Объединяем списки на уровне Python
    all_songs = list(songs) + list(liked_songs)
    # Сортируем по created_at
    all_songs = sorted(all_songs, key=lambda x: x.created_at, reverse=True)

    if request.method == 'POST' and is_own_profile:
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('store:profile', username=username)
        else:
            messages.error(request, 'Ошибка при обновлении профиля. Проверьте данные.')
    else:
        form = ProfileForm(instance=profile)

    # Формируем JSON для песен
    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
        for song in all_songs
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
    return render(request, 'store/delete_music.html', {'song': song})

# Лайк песни
@login_required
@require_POST
@csrf_protect
def like_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        user = request.user
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
        }, status=500)

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
        cart, created = Cart.objects.get_or_create(user=request.user)
        if Transaction.objects.filter(buyer=request.user, song=song, is_successful=True).exists():
            logger.debug(f"Песня {song_id} уже куплена пользователем {request.user.username}")
            messages.warning(request, f'Песня "{song.title}" уже куплена.')
            return redirect('store:cart')
        if song not in cart.songs.all():
            cart.songs.add(song)
            logger.debug(f"Пользователь {user.username} добавил песню {song_id} в корзину")
            messages.success(request, f'Песня "{song.title}" добавлена в корзину.')
            return redirect('store:cart')
        logger.debug(f"Песня {song_id} уже в корзине пользователя {request.user.username}")
        messages.info(request, f'Песня "{song.title}" уже в корзине.')
        return redirect('store:cart')
    except Exception as e:
        logger.error(f"Ошибка в add_to_cart для song_id {song_id}: {str(e)}")
        messages.error(request, f'Произошла ошибка при добавлении в корзину: {str(e)}')
        return redirect('store:cart')

# Удаление из корзины
@login_required
@require_POST
@csrf_protect
def remove_from_cart(request, song_id):
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        song = get_object_or_404(Song, id=song_id)
        if song in cart.songs.all():
            cart.songs.remove(song)
            logger.debug(f"Песня {song_id} удалена из корзины пользователя {request.user.username}")
            messages.success(request, 'Песня удалена из корзины.')
            return redirect('store:cart')
        logger.debug(f"Песня {song_id} не найдена в корзине пользователя {request.user.username}")
        messages.warning(request, 'Песня не найдена в корзине.')
        return redirect('store:cart')
    except Exception as e:
        logger.error(f"Ошибка в remove_from_cart для song_id {song_id}: {str(e)}")
        messages.error(request, f'Произошла ошибка при удалении из корзины: {str(e)}')
        return redirect('store:cart')

# Корзина
@login_required
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    songs = cart.songs.select_related('author').all()
    total_price = sum(song.price for song in songs)
    
    # Получаем историю покупок пользователя
    purchases = Purchase.objects.filter(user=request.user).select_related('user').prefetch_related('songs__author').order_by('-purchase_date')
    
    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
        for song in songs
    ]
    
    context = {
        'songs': songs,
        'total_price': total_price,
        'purchases': purchases,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/cart.html', context)

# Покупка одной песни
@login_required
def buy_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    user = request.user
    if Transaction.objects.filter(buyer=user, song=song, is_successful=True).exists():
        messages.error(request, 'Вы уже приобрели эту песню.')
        return redirect('store:cart')
    if request.method == 'POST':
        if user.balance < song.price:
            messages.error(request, f"Недостаточно средств. Ваш баланс: ₽{user.balance:.2f}. Необходимо: ₽{song.price:.2f}.")
            return redirect('store:top_up_balance')
        try:
            with transaction.atomic():
                user.balance -= song.price
                user.save()
                song.author.balance += song.price
                song.author.save()
                purchase = Purchase.objects.create(
                    user=user,
                    total_price=song.price
                )
                purchase.songs.add(song)
                Transaction.objects.create(
                    buyer=user,
                    song=song,
                    amount=song.price,
                    is_successful=True
                )
                Contract.objects.create(
                    purchase=purchase,
                    buyer=user,
                    author=song.author,
                    song=song,
                    amount=song.price,
                    is_accepted_by_buyer=True
                )
                cart, created = Cart.objects.get_or_create(user=user)
                cart.songs.remove(song)
                messages.success(request, 'Песня успешно приобретена! Договор сформирован.')
                return redirect('store:purchase_contract', purchase_id=purchase.id)
        except Exception as e:
            logger.error(f"Ошибка в buy_song для song_id {song_id}: {str(e)}")
            messages.error(request, f'Ошибка при покупке: {str(e)}')
            return redirect('store:cart')
    songs_json = [
        {
            'id': song.id,
            'path': song.path.url,
            'title': song.title,
            'author': song.author.username,
            'total_likes': song.total_likes,
            'price': float(song.price),
            'total_plays': song.total_plays,
            'cover': song.cover.url if song.cover else '/static/images/default_cover.jpg'
        }
    ]
    context = {
        'song': song,
        'user_balance': user.balance,
        'songs_json': json.dumps(songs_json, ensure_ascii=False),
    }
    return render(request, 'store/buy_song.html', context)

# Обработка покупки (корзина)
@login_required
def process_purchase(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    songs = cart.songs.select_related('author').all()
    if not songs:
        messages.error(request, "Ваша корзина пуста.")
        return redirect('store:cart')
    total_price = sum(song.price for song in songs)
    if request.user.balance < total_price:
        messages.error(request, f"Недостаточно средств. Ваш баланс: ₽{request.user.balance:.2f}. Необходимо: ₽{total_price:.2f}.")
        return redirect('store:top_up_balance')
    if request.method == 'POST':
        try:
            with transaction.atomic():
                request.user.balance -= total_price
                request.user.save()
                purchase = Purchase.objects.create(
                    user=request.user,
                    total_price=total_price
                )
                purchase.songs.set(songs)
                for song in songs:
                    if not Transaction.objects.filter(buyer=request.user, song=song, is_successful=True).exists():
                        Transaction.objects.create(
                            buyer=request.user,
                            song=song,
                            amount=song.price,
                            is_successful=True
                        )
                        Contract.objects.create(
                            purchase=purchase,
                            buyer=request.user,
                            author=song.author,
                            song=song,
                            amount=song.price,
                            is_accepted_by_buyer=True
                        )
                        song.author.balance += song.price
                        song.author.save()
                cart.songs.clear()
                messages.success(request, "Покупка успешно завершена! Договор сформирован.")
                return redirect('store:purchase_contract', purchase_id=purchase.id)
        except Exception as e:
            logger.error(f"Ошибка в process_purchase для пользователя {request.user.username}: {str(e)}")
            messages.error(request, f"Ошибка при обработке покупки: {str(e)}")
            return redirect('store:cart')
    context = {
        'songs': songs,
        'total_price': total_price,
    }
    return render(request, 'store/process_purchase.html', context)

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
            messages.success(request, f'Баланс успешно пополнен на ₽{amount:.2f}.')
            logger.debug(f"Пользователь {user.username} пополнил баланс на {amount}")
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

# Добавление в плейлист
@login_required
@require_POST
@csrf_protect
def add_to_playlist(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
        playlist = get_object_or_404(Playlist, user=request.user)
        if song in playlist.songs.all():
            logger.debug(f"Песня {song_id} уже в плейлисте пользователя {request.user.username}")
            return JsonResponse({
                'success': False,
                'message': f'Песня "{song.title}" уже в плейлисте',
                'in_playlist': True
            }, status=200)
        playlist.songs.add(song)
        logger.debug(f"Пользователь {user.username} добавил песню {song_id} в плейлист")
        return JsonResponse({
            'success': True,
            'message': f'Песня "{song.title}" добавлена в плейлист',
            'in_playlist': True
        }, status=200)
    except Exception as e:
        logger.error(f"Ошибка в add_to_playlist для song_id {song_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Произошла ошибка при добавлении в плейлист: {str(e)}',
            'error': str(e)
        }, status=500)

# Просмотр договора
@login_required
def purchase_contract(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id, user=request.user)
    context = {
        'purchase': purchase,
        'songs': purchase.songs.select_related('author').all(),
        'total_price': purchase.total_price,
    }
    return render(request, 'store/purchase_contract.html', context)

# Подтверждение договора автором
@login_required
def accept_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, author=request.user)
    if request.method == 'POST':
        contract.is_accepted_by_author = True
        contract.save()
        messages.success(request, f"Договор для песни '{contract.song.title}' подтверждён.")
        return redirect('store:profile', username=request.user.username)
    return render(request, 'store/accept_contract.html', {'contract': contract})

# Скачивание PDF-версии договора
@login_required
def download_contract_pdf(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id, user=request.user)
    context = {
        'purchase': purchase,
        'songs': purchase.songs.select_related('author').all(),
        'total_price': purchase.total_price,
        'request': request,
    }
    html_string = render_to_string('store/purchase_contract.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="contract_{purchase_id}.pdf"'
    return response