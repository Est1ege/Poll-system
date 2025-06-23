from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.db.models import Q
from .forms import UserRegistrationForm, CustomPasswordResetForm, CustomSetPasswordForm
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from polls.models import Poll, Vote
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import ensure_csrf_cookie


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            redirect_url = request.GET.get('next', 'home')
            return redirect(redirect_url)
        else:
            messages.error(request, "Username Or Password is incorrect!",
                           extra_tags='alert alert-warning alert-dismissible fade show')

    return render(request, 'accounts/login.html')


def logout_user(request):
    logout(request)
    return redirect('home')


def create_user(request):
    if request.method == 'POST':
        check1 = False
        check2 = False
        check3 = False
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            email = form.cleaned_data['email']

            if password1 != password2:
                check1 = True
                messages.error(request, 'Password did not match!',
                               extra_tags='alert alert-warning alert-dismissible fade show')
            if User.objects.filter(username=username).exists():
                check2 = True
                messages.error(request, 'Username already exists!',
                               extra_tags='alert alert-warning alert-dismissible fade show')
            if User.objects.filter(email=email).exists():
                check3 = True
                messages.error(request, 'Email already registered!',
                               extra_tags='alert alert-warning alert-dismissible fade show')

            if check1 or check2 or check3:
                messages.error(
                    request, "Registration Failed!", extra_tags='alert alert-warning alert-dismissible fade show')
                return redirect('accounts:register')
            else:
                user = User.objects.create_user(
                    username=username, password=password1, email=email)
                messages.success(
                    request, f'Thanks for registering {user.username}.', extra_tags='alert alert-success alert-dismissible fade show')
                return redirect('accounts:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@ensure_csrf_cookie
def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = CustomPasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "accounts/password_reset_email.html"
                    c = {
                        "email": user.email,
                        'domain': request.META['HTTP_HOST'],
                        'site_name': 'PollMe Beauty',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'https' if request.is_secure() else 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, 'noreply@pollme.com', [user.email], fail_silently=False)
                    except Exception as e:
                        messages.error(request, f"Error sending email: {e}")
                        return redirect("accounts:password_reset")
                    messages.success(request, "Password reset email has been sent.")
                    return redirect("accounts:login")
            else:
                messages.error(request, "An invalid email has been entered.")
    password_reset_form = CustomPasswordResetForm()
    return render(request=request, template_name="accounts/password_reset.html", context={"password_reset_form": password_reset_form})


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been set. You may go ahead and log in now.")
                return redirect('accounts:login')
        else:
            form = CustomSetPasswordForm(user)
        return render(request, 'accounts/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, "The reset link was invalid, possibly because it has already been used.")
        return redirect('accounts:login')


@login_required
def profile(request):
    # Статистика пользователя
    user_polls_count = Poll.objects.filter(owner=request.user).count()
    total_votes_received = sum(poll.get_vote_count for poll in Poll.objects.filter(owner=request.user))
    user_votes_count = Vote.objects.filter(user=request.user).count()
    
    # Количество дней с регистрации
    days_registered = (timezone.now() - request.user.date_joined).days
    
    # Недавние опросы пользователя (последние 5)
    recent_polls = Poll.objects.filter(owner=request.user).order_by('-pub_date')[:5]
    
    context = {
        'user': request.user,
        'user_polls_count': user_polls_count,
        'total_votes_received': total_votes_received,
        'user_votes_count': user_votes_count,
        'days_registered': days_registered,
        'recent_polls': recent_polls,
    }
    
    return render(request, 'accounts/profile.html', context)
