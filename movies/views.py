from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from .models import Movie, Genre, Comment, Favorite, UserRating
from .forms import RegisterForm, CommentForm, RatingForm, ReplyForm, CustomPasswordResetForm, CustomSetPasswordForm


def register(request):
    if request.user.is_authenticated:
        return redirect('movie_list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '✅ Регистрация прошла успешно!')
            return redirect('movie_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegisterForm()

    return render(request, 'movies/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('movie_list')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, '❌ Пожалуйста, заполните все поля')
            return render(request, 'movies/login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'✅ Добро пожаловать, {username}!')
            return redirect('movie_list')
        else:
            messages.error(request, '❌ Неверное имя пользователя или пароль')
            return render(request, 'movies/login.html')

    return render(request, 'movies/login.html')


def user_logout(request):
    logout(request)
    messages.success(request, '✅ Вы успешно вышли из аккаунта!')
    return redirect('movie_list')


def movie_list(request):
    movies = Movie.objects.all()

    search_query = request.GET.get('search', '')
    if search_query:
        movies = movies.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(director__icontains=search_query)
        )

    genre_filter = request.GET.get('genre', '')
    if genre_filter:
        movies = movies.filter(genres__id=genre_filter)

    paginator = Paginator(movies, 12)
    page_number = request.GET.get('page', 1)
    movies_page = paginator.get_page(page_number)

    genres = Genre.objects.all()

    context = {
        'movies': movies_page,
        'genres': genres,
        'search_query': search_query,
        'selected_genre': genre_filter,
    }
    return render(request, 'movies/movie_list.html', context)


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    comments = movie.comments.filter(parent__isnull=True).order_by('-created_at')  # Только родительские комментарии
    is_favorite = False
    user_rating = None

    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, movie=movie).exists()
        user_rating = movie.get_user_rating(request.user)

    # Обработка комментария
    if request.method == 'POST':
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.user = request.user
                comment.movie = movie
                comment.save()
                messages.success(request, '💬 Комментарий добавлен!')
                return redirect('movie_detail', movie_id=movie.id)

        # Обработка ответа на комментарий
        elif 'reply_submit' in request.POST:
            reply_form = ReplyForm(request.POST)
            parent_id = request.POST.get('parent_id')
            if reply_form.is_valid() and parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                reply = reply_form.save(commit=False)
                reply.user = request.user
                reply.movie = movie
                reply.parent = parent_comment
                reply.save()
                messages.success(request, '💬 Ответ добавлен!')
                return redirect('movie_detail', movie_id=movie.id)

        # Обработка рейтинга
        elif 'rating_submit' in request.POST:
            try:
                score = int(request.POST.get('score'))
                if 1 <= score <= 10:
                    user_rating_obj, created = UserRating.objects.update_or_create(
                        user=request.user,
                        movie=movie,
                        defaults={'score': score}
                    )
                    avg_rating = movie.user_ratings.aggregate(Avg('score'))['score__avg']
                    movie.rating = round(avg_rating, 1)
                    movie.save()
                    messages.success(request, f'⭐ Вы оценили фильм на {score} из 10!')
                else:
                    messages.error(request, 'Оценка должна быть от 1 до 10')
            except ValueError:
                messages.error(request, 'Пожалуйста, выберите корректную оценку')
            return redirect('movie_detail', movie_id=movie.id)

    context = {
        'movie': movie,
        'comments': comments,
        'comment_form': CommentForm(),
        'reply_form': ReplyForm(),
        'rating_form': RatingForm(),
        'is_favorite': is_favorite,
        'user_rating': user_rating,
    }
    return render(request, 'movies/movie_detail.html', context)


# Представления для восстановления пароля
class CustomPasswordResetView(PasswordResetView):
    template_name = 'movies/password_reset.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'movies/password_reset_email.html'
    subject_template_name = 'movies/password_reset_subject.txt'


def password_reset_done(request):
    return render(request, 'movies/password_reset_done.html')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'movies/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')


def password_reset_complete(request):
    messages.success(request, '✅ Пароль успешно изменен! Теперь вы можете войти.')
    return redirect('login')


# Остальные функции (add_to_favorites, remove_from_favorites, favorites_list)
@login_required
def add_to_favorites(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, movie=movie)

    if created:
        messages.success(request, f'❤️ Фильм "{movie.title}" добавлен в избранное!')
    else:
        messages.info(request, f'Фильм "{movie.title}" уже в избранном')

    return redirect(request.META.get('HTTP_REFERER', 'movie_list'))


@login_required
def remove_from_favorites(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Favorite.objects.filter(user=request.user, movie=movie).delete()
    messages.success(request, f'💔 Фильм "{movie.title}" удален из избранного')
    return redirect(request.META.get('HTTP_REFERER', 'movie_list'))


@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('movie')
    movies = [fav.movie for fav in favorites]

    paginator = Paginator(movies, 12)
    page_number = request.GET.get('page', 1)
    movies_page = paginator.get_page(page_number)

    return render(request, 'movies/favorites.html', {'movies': movies_page})