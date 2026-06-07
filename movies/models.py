from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


class Genre(models.Model):
    name = models.CharField('Название жанра', max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'


class Movie(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    poster_url = models.URLField('Ссылка на постер', blank=True, null=True)
    poster_image = models.ImageField('Постер', upload_to='posters/', blank=True, null=True)
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=1, default=0.0)
    genres = models.ManyToManyField(Genre, verbose_name='Жанры', related_name='movies')
    release_year = models.IntegerField('Год выпуска')
    director = models.CharField('Режиссер', max_length=200, blank=True)
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    def get_poster(self):
        if self.poster_image:
            return self.poster_image.url
        return self.poster_url or 'https://via.placeholder.com/300x450?text=No+Poster'

    def get_average_rating(self):
        ratings = self.user_ratings.all()
        if ratings.exists():
            avg = ratings.aggregate(models.Avg('score'))['score__avg']
            return round(avg, 1)
        return self.rating

    def get_user_rating(self, user):
        if user.is_authenticated:
            rating = self.user_ratings.filter(user=user).first()
            return rating.score if rating else None
        return None

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('movie_detail', args=[str(self.id)])

    class Meta:
        verbose_name = 'Фильм'
        verbose_name_plural = 'Фильмы'
        ordering = ['-rating', '-created_at']


class UserRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_ratings', verbose_name='Пользователь')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='user_ratings', verbose_name='Фильм')
    score = models.IntegerField('Оценка', validators=[MinValueValidator(1), MaxValueValidator(10)])
    created_at = models.DateTimeField('Дата оценки', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        unique_together = ['user', 'movie']
        verbose_name = 'Оценка пользователя'
        verbose_name_plural = 'Оценки пользователей'

    def __str__(self):
        return f'{self.user.username} оценил {self.movie.title} на {self.score}'


class Comment(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments', verbose_name='Фильм')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name='Пользователь')
    text = models.TextField('Текст комментария')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies',
                               verbose_name='Ответ на')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.movie.title}'

    def get_replies(self):
        return self.replies.all().order_by('created_at')

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='Пользователь')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='Фильм')
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    class Meta:
        unique_together = ['user', 'movie']
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user.username} - {self.movie.title}'