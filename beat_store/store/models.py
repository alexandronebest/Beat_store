from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Count, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Баланс')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        indexes = [models.Index(fields=['username', 'email'])]

    def __str__(self):
        return self.username

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Название')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'

class Song(models.Model):
    title = models.CharField(max_length=100, verbose_name='Название')
    path = models.FileField(upload_to='songs/', verbose_name='Файл')
    cover = models.ImageField(upload_to='covers/', null=True, blank=True, verbose_name='Обложка')
    likes = models.ManyToManyField(
        User,
        related_name='liked_songs',
        blank=True,
        verbose_name='Лайки'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='songs',
        verbose_name='Автор'
    )
    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Жанр'
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name='Цена'
    )
    total_plays = models.PositiveIntegerField(default=0, verbose_name='Количество прослушиваний')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return self.title

    @property
    def total_likes(self):
        return self.likes.count()

    class Meta:
        verbose_name = 'Песня'
        verbose_name_plural = 'Песни'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['total_plays']),
            models.Index(fields=['author', 'created_at']),
        ]

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Статус'
    )
    photo = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True,
        verbose_name='Фото'
    )

    def __str__(self):
        return f'Профиль {self.user.username}'

    @property
    def total_likes(self):
        return self.user.songs.aggregate(total=Count('likes'))['total'] or 0

    @property
    def total_plays(self):
        return self.user.songs.aggregate(total=Sum('total_plays'))['total'] or 0

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

class Playlist(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='playlists',
        verbose_name='Пользователь'
    )
    songs = models.ManyToManyField(
        Song,
        related_name='playlists',
        blank=True,
        verbose_name='Песни'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f'Плейлист {self.user.username}'

    class Meta:
        verbose_name = 'Плейлист'
        verbose_name_plural = 'Плейлисты'

class Transaction(models.Model):
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchases',
        verbose_name='Покупатель'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Песня'
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Сумма'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата покупки')
    is_successful = models.BooleanField(default=False, verbose_name='Успешно')

    def __str__(self):
        return f'{self.buyer.username} купил {self.song.title} за {self.amount}'

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'

class Purchase(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bulk_purchases',
        verbose_name='Покупатель'
    )
    songs = models.ManyToManyField(
        Song,
        related_name='purchases',
        verbose_name='Песни'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Общая сумма'
    )
    purchase_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата покупки'
    )

    def __str__(self):
        return f"Purchase by {self.user.username} on {self.purchase_date}"

    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'

class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )
    songs = models.ManyToManyField(
        Song,
        related_name='carts',
        blank=True,
        verbose_name='Песни'
    )

    def __str__(self):
        return f'Cart of {self.user.username}'

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Cart.objects.create(user=instance)