from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.db import IntegrityError
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
import json
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db import transaction
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.urls import reverse
from django import forms
from django.db.models.functions import TruncMonth
from django.contrib.auth.models import User

from .models import Poll, Choice, Vote, PollInvitation, Discussion, UserGroup, PollAccess, Question
from .forms import PollAddForm, EditPollForm, ChoiceAddForm, PollInvitationForm, DiscussionForm, UserGroupForm, PollAccessForm, QuestionFormSet, ChoiceFormSet


@login_required
def poll_list(request):
    try:
        all_polls = Poll.objects.all().order_by('-pub_date')
        search_term = ''
        
        user_id = request.GET.get('user')
        if user_id:
            all_polls = all_polls.filter(owner__id=user_id)

        if 'name' in request.GET:
            all_polls = all_polls.order_by('text')
        if 'date' in request.GET:
            all_polls = all_polls.order_by('pub_date')
        if 'vote' in request.GET:
            all_polls = all_polls.annotate(vote_count=Count('questions__vote')).order_by('vote_count')
        if 'search' in request.GET:
            search_term = request.GET['search']
            all_polls = all_polls.filter(text__icontains=search_term)

        # Добавляем информацию о том, проголосовал ли пользователь в каждом опросе
        for poll in all_polls:
            poll.user_has_voted = poll.user_can_vote(request.user) == False
            poll.is_owner = poll.owner == request.user

        paginator = Paginator(all_polls, 6)
        page = request.GET.get('page')
        polls = paginator.get_page(page)

        params = request.GET.copy()
        params.pop('page', None)

        print(f"[INFO] Список опросов отображен для пользователя {request.user.username}")
        return render(request, 'polls/polls_list.html', {
            'polls': polls,
            'params': params.urlencode(),
            'search_term': search_term,
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_list: {str(e)}")
        messages.error(request, f"Ошибка при отображении списка опросов: {e}")
        return render(request, 'polls/polls_list.html', {
            'polls': [],
            'params': '',
            'search_term': '',
        })


@login_required
def list_by_user(request):
    try:
        # Опросы, созданные пользователем
        owned_polls = Poll.objects.filter(owner=request.user).order_by('-pub_date')
        
        # Опросы, в которых пользователь проголосовал
        voted_polls = Poll.objects.filter(
            questions__vote__user=request.user
        ).distinct().order_by('-pub_date')
        
        # Опросы, доступные для голосования (не созданные пользователем и не проголосованные)
        available_polls = Poll.objects.filter(
            active=True
        ).exclude(
            owner=request.user
        ).exclude(
            questions__vote__user=request.user
        ).distinct().order_by('-pub_date')
        
        # Добавляем информацию о статусе для каждого опроса
        for poll in owned_polls:
            poll.is_owner = True
            poll.user_has_voted = False
        
        for poll in voted_polls:
            poll.is_owner = False
            poll.user_has_voted = True
        
        for poll in available_polls:
            poll.is_owner = False
            poll.user_has_voted = False
        
        print(f"[INFO] Дашборд пользователя отображен для {request.user.username}")
        return render(request, 'polls/user_polls.html', {
            'owned_polls': owned_polls,
            'voted_polls': voted_polls,
            'available_polls': available_polls,
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в list_by_user: {str(e)}")
        messages.error(request, f"Ошибка при отображении дашборда: {e}")
        return redirect('polls:list')


@login_required
@ensure_csrf_cookie
def poll_add(request):
    if not request.user.has_perm('polls.add_poll'):
        print(f"[ERROR] Пользователь {request.user.username} не имеет права на добавление опроса")
        return render(request, 'polls/no_permission.html', status=403)

    if request.method == 'POST':
        print(f"[INFO] Получен POST запрос от пользователя {request.user.username}")
        print(f"[INFO] POST данные: {request.POST}")
        form = PollAddForm(request.POST)
        question_formset = QuestionFormSet(request.POST, prefix='question_set')
        print(f"[INFO] Форма валидна: {form.is_valid()}")
        if not form.is_valid():
            print(f"[ERROR] Ошибки формы: {form.errors}")
            print(f"[ERROR] Ошибки non-field: {form.non_field_errors()}")
        if form.is_valid():
            try:
                with transaction.atomic():
                    poll = form.save(commit=False)
                    poll.owner = request.user
                    poll.save()
                    print(f"[INFO] Опрос создан: {poll.text[:50]}...")
                    if poll.is_multi_question:
                        print("[INFO] Создание многовопросного опроса")
                        if question_formset.is_valid():
                            question_formset.instance = poll
                            questions = question_formset.save()
                            print(f"[INFO] Создано вопросов: {len(questions)}")
                            for i, question in enumerate(questions):
                                choice_index = 0
                                while True:
                                    choice_text_key = f'choices_{i}-{choice_index}-choice_text'
                                    if choice_text_key not in request.POST or not request.POST[choice_text_key]:
                                        break
                                    choice_text = request.POST[choice_text_key]
                                    order = request.POST.get(f'choices_{i}-{choice_index}-order', choice_index + 1)
                                    is_correct = f'choices_{i}-{choice_index}-is_correct' in request.POST
                                    Choice.objects.create(
                                        question=question,
                                        choice_text=choice_text,
                                        order=order,
                                        is_correct=is_correct
                                    )
                                    choice_index += 1
                                print(f"[INFO] Создано вариантов ответов для вопроса {i+1}: {choice_index}")
                        else:
                            print(f"[ERROR] Ошибки формсета: {question_formset.errors}")
                            error_list = []
                            if question_formset.non_form_errors():
                                error_list.extend(list(question_formset.non_form_errors()))
                            for form_errors in question_formset.errors:
                                if form_errors:
                                    error_list.append(str(form_errors))
                            if not error_list:
                                error_list.append(_("Invalid question data (unknown error)."))
                            raise forms.ValidationError(error_list)
                    else:
                        print("[INFO] Создание обычного опроса")
                        question = Question.objects.create(
                            poll=poll,
                            text=poll.text,
                            order=1,
                            is_required=True
                        )
                        print(f"[INFO] Создан вопрос: {question.text[:50]}...")
                        choices_created = 0
                        for i in range(1, 11):
                            choice_text = form.cleaned_data.get(f'choice{i}')
                            is_correct = form.cleaned_data.get(f'choice{i}_correct', False)
                            if choice_text:
                                Choice.objects.create(
                                    question=question,
                                    choice_text=choice_text,
                                    is_correct=is_correct,
                                    order=i
                                )
                                choices_created += 1
                        print(f"[INFO] Создано вариантов ответов: {choices_created}")
                messages.success(request, _("Poll & Choices added successfully."),
                                 extra_tags='alert alert-success')
                print("[INFO] Опрос успешно создан, перенаправление на список")
                return redirect('polls:list')
            except forms.ValidationError as e:
                error_message = " ".join(e.messages)
                messages.error(request, f"{error_message}", extra_tags='alert alert-danger')
                print(f"[ERROR] Ошибка валидации: {error_message}")
            except Exception as e:
                messages.error(request, f"Error creating poll: {str(e)}",
                               extra_tags='alert alert-danger')
                print(f"[ERROR] Общая ошибка: {str(e)}")
    else:
        print(f"[INFO] GET запрос от пользователя {request.user.username}")
        form = PollAddForm()
        question_formset = QuestionFormSet(prefix='question_set', queryset=Question.objects.none())
    
    return render(request, 'polls/add_poll.html', {
        'form': form,
        'question_formset': question_formset,
    })


@login_required
def poll_edit(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if request.user != poll.owner:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            return redirect('home')
        if request.method == 'POST':
            form = EditPollForm(request.POST, instance=poll)
            if form.is_valid():
                form.save()
                messages.success(request, _("Poll updated successfully."),
                                 extra_tags='alert alert-success')
                print(f"[INFO] Опрос {slug} успешно обновлён")
                return redirect('polls:list')
            else:
                print(f"[ERROR] Ошибки формы при редактировании: {form.errors}")
        else:
            form = EditPollForm(instance=poll)
        return render(request, 'polls/poll_edit.html', {'form': form, 'poll': poll})
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_edit: {str(e)}")
        messages.error(request, f"Ошибка при редактировании опроса: {e}")
        return redirect('polls:list')


@login_required
def poll_delete(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if poll.owner != request.user:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            messages.error(request, _("You do not have permission to delete this poll."))
            return redirect('polls:list')
        if request.method == 'POST':
            poll_text = poll.text
            poll.delete()
            messages.success(request, _("Poll '%(poll_text)s' has been deleted successfully.") % {'poll_text': poll_text})
            print(f"[INFO] Опрос {slug} удалён")
            return redirect('polls:list')
        print(f"[INFO] GET запрос на удаление опроса {slug}, перенаправление")
        return redirect('polls:detail', slug=slug)
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_delete: {str(e)}")
        messages.error(request, f"Ошибка при удалении опроса: {e}")
        return redirect('polls:list')


@login_required
def add_choice(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')

    if request.method == 'POST':
        form = ChoiceAddForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            # Для обычных опросов используем первый вопрос
            if poll.is_multi_question:
                # Нужно выбрать вопрос для многовопросного опроса
                pass
            else:
                question = poll.questions.first()
                if question:
                    choice.question = question
                    choice.save()
                    messages.success(request, _("Choice added successfully."),
                                     extra_tags='alert alert-success')
                    return redirect('polls:edit', slug=poll.slug)
    else:
        form = ChoiceAddForm()

    return render(request, 'polls/add_choice.html', {
        'form': form,
        'poll': poll,
        'edit_choice': False,
    })


@login_required
def choice_edit(request, choice_id):
    choice = get_object_or_404(Choice, pk=choice_id)
    poll = choice.question.poll
    if request.user != poll.owner:
        return redirect('home')

    if request.method == 'POST':
        form = ChoiceAddForm(request.POST, instance=choice)
        if form.is_valid():
            form.save()
            messages.success(request, _("Choice updated successfully."),
                             extra_tags='alert alert-success')
            return redirect('polls:edit', slug=poll.slug)
    else:
        form = ChoiceAddForm(instance=choice)

    return render(request, 'polls/add_choice.html', {
        'form': form,
        'poll': poll,
        'edit_choice': True,
        'choice': choice,
    })


@login_required
def choice_delete(request, choice_id):
    choice = get_object_or_404(Choice, pk=choice_id)
    poll = choice.question.poll
    if request.user != poll.owner:
        return redirect('home')
    choice.delete()
    messages.success(request, _("Choice deleted successfully."),
                     extra_tags='alert alert-success')
    return redirect('polls:edit', slug=poll.slug)


def poll_detail(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if not poll.active:
            print(f"[INFO] Опрос {slug} неактивен, перенаправление на результаты")
            return redirect('polls:results', slug=slug)
        
        # Получаем все вопросы опроса
        questions = poll.questions.all().order_by('order')
        
        # Проверяем, проголосовал ли пользователь
        user_has_voted = False
        if request.user.is_authenticated:
            user_has_voted = not poll.user_can_vote(request.user)
        
        # Проверяем, является ли пользователь владельцем
        is_owner = request.user.is_authenticated and poll.owner == request.user
        
        print(f"[INFO] Детали опроса {slug} отображены для пользователя {request.user.username}")
        return render(request, 'polls/poll_detail.html', {
            'poll': poll,
            'questions': questions,
            'user_has_voted': user_has_voted,
            'is_owner': is_owner,
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_detail: {str(e)}")
        messages.error(request, f"Ошибка при отображении опроса: {e}")
        return redirect('polls:list')


@login_required
def poll_vote(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if not poll.user_can_vote(request.user):
            print(f"[INFO] Пользователь {request.user.username} уже голосовал в опросе {slug}")
            return render(request, 'polls/already_voted.html', {'poll': poll})
        if request.method != 'POST':
            print(f"[INFO] Не POST запрос на голосование, перенаправление")
            return redirect('polls:detail', slug=slug)
        questions = poll.questions.all()
        for question in questions:
            choice_id = request.POST.get(f'question-{question.id}')
        if not choice_id:
            print(f"[ERROR] Не выбран вариант для вопроса {question.id}")
            messages.error(request, _("Please select an answer for all questions!"),
                   extra_tags='alert alert-warning')
            return redirect('polls:detail', slug=slug)
        try:
            for question in questions:
                choice_id = request.POST.get(f'question-{question.id}')
                choice = get_object_or_404(Choice, pk=choice_id, question=question)
                existing_vote = Vote.objects.filter(user=request.user, question=question).first()
                if existing_vote:
                    existing_vote.choice = choice
                    existing_vote.save()
                else:
                    Vote.objects.create(user=request.user, question=question, choice=choice)
            print(f"[INFO] Пользователь {request.user.username} проголосовал в опросе {slug}")
        except IntegrityError as e:
            print(f"[ERROR] IntegrityError при голосовании: {str(e)}")
        return render(request, 'polls/already_voted.html', {'poll': poll})
    except Exception as e:
        print(f"[ERROR] Ошибка при голосовании: {str(e)}")
        messages.error(request, f"Ошибка при голосовании: {e}")
        return redirect('polls:detail', slug=slug)
    return redirect('polls:results', slug=poll.slug)


@login_required
def end_poll(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')
    poll.active = False
    poll.save()
    # показываем unified results
    return render(request, 'polls/results.html', {'poll': poll})


def results_view(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        
        # Получаем все вопросы с их вариантами ответов и статистикой
        questions_data = []
        for question in poll.questions.all().order_by('order'):
            choices_data = []
            total_votes_for_question = question.vote_set.count()
            
            # Получаем голос текущего пользователя для этого вопроса
            user_vote = None
            if request.user.is_authenticated:
                user_vote = question.vote_set.filter(user=request.user).first()
            
            for choice in question.choices.all().order_by('order'):
                votes = choice.vote_set.count()
                percentage = (votes / total_votes_for_question * 100) if total_votes_for_question > 0 else 0
                
                # Определяем, выбрал ли пользователь этот вариант и правильный ли он
                is_user_choice = user_vote and user_vote.choice == choice
                is_correct = choice.is_correct
                is_wrong_user_choice = is_user_choice and not is_correct
                
                choices_data.append({
                    'choice': choice,
                    'votes': votes,
                    'percentage': round(percentage, 1),
                    'is_user_choice': is_user_choice,
                    'is_correct': is_correct,
                    'is_wrong_user_choice': is_wrong_user_choice
                })
            
            questions_data.append({
                'question': question,
                'choices': choices_data,
                'total_votes': total_votes_for_question,
                'user_vote': user_vote
            })
        
        return render(request, 'polls/results.html', {
            'poll': poll,
            'questions_data': questions_data,
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в results_view: {str(e)}")
        messages.error(request, f"Ошибка при отображении результатов: {e}")
        return redirect('polls:list')


@login_required
def poll_invite(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if request.user != poll.owner:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            return redirect('home')
        if request.method == 'POST':
            form = PollInvitationForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                token = get_random_string(64)
                invitation = PollInvitation.objects.create(
                    poll=poll,
                    email=email,
                    token=token
                )
                subject = f"Приглашение на голосование: {poll.text}"
                message = render_to_string('polls/email/invitation.html', {
                    'poll': poll,
                    'invitation': invitation,
                    'site_url': request.get_host()
                })
                send_mail(subject, message, 'noreply@example.com', [email])
                messages.success(request, _("Invitation sent successfully."))
                print(f"[INFO] Приглашение отправлено на {email}")
                return redirect('polls:detail', slug=slug)
            else:
                print(f"[ERROR] Ошибки формы приглашения: {form.errors}")
        else:
            form = PollInvitationForm()
        return render(request, 'polls/invite.html', {
            'form': form,
            'poll': poll
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_invite: {str(e)}")
        messages.error(request, f"Ошибка при отправке приглашения: {e}")
        return redirect('polls:list')


@login_required
def poll_discussion(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    
    if not poll.allow_discussion:
        return redirect('polls:detail', slug=slug)

    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.poll = poll
            discussion.user = request.user
            discussion.save()
            return redirect('polls:discussion', slug=slug)
    else:
        form = DiscussionForm()

    discussions = poll.discussion_set.all()
    
    return render(request, 'polls/discussion.html', {
        'poll': poll,
        'discussions': discussions,
        'form': form
    })


@login_required
def poll_analytics(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if request.user != poll.owner:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            return redirect('home')

        # Получаем данные по всем вопросам
        questions_data = []
        total_votes = poll.get_vote_count
        
        for question in poll.questions.all().order_by('order'):
            choices_data = []
            question_votes = question.vote_set.count()
            
            for choice in question.choices.all().order_by('order'):
                votes = choice.vote_set.count()
                percentage = (votes / question_votes * 100) if question_votes > 0 else 0
                choices_data.append({
                    'choice': choice.choice_text,
                    'votes': votes,
                    'percentage': round(percentage, 2),
                    'is_correct': choice.is_correct
                })
            
            questions_data.append({
                'question': question.text,
                'choices': choices_data,
                'total_votes': question_votes
            })
        
        # Временная статистика
        votes_by_date = Vote.objects.filter(question__poll=poll).extra(
            select={'date': 'date(polls_vote.created_at)'}
        ).values('date').annotate(count=Count('id')).order_by('date')

        context = {
            'poll': poll,
            'total_votes': total_votes,
            'questions_data': questions_data,
            'votes_by_date': list(votes_by_date),
        }
        print(f"[INFO] Аналитика по опросу {slug} отображена")
        return render(request, 'polls/analytics.html', context)
    except Exception as e:
        print(f"[ERROR] Ошибка в poll_analytics: {str(e)}")
        messages.error(request, f"Ошибка при отображении аналитики: {e}")
        return redirect('polls:list')


@login_required
def export_results(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if request.user != poll.owner:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            return redirect('home')

        format_type = request.GET.get('format', 'json')
        
        # Подготавливаем данные для экспорта
        data = {
            'poll': {
                'text': poll.text,
                'description': poll.description,
                'created_at': poll.created_at.isoformat(),
                'end_date': poll.end_date.isoformat() if poll.end_date else None,
                'total_votes': poll.get_vote_count,
                'is_quiz': poll.is_quiz,
                'is_multi_question': poll.is_multi_question,
            },
            'questions': []
        }
        
        # Добавляем данные по каждому вопросу
        for question in poll.questions.all().order_by('order'):
            question_data = {
                'text': question.text,
                'order': question.order,
                'total_votes': question.vote_set.count(),
                'choices': []
            }
            
            for choice in question.choices.all().order_by('order'):
                votes = choice.vote_set.count()
                percentage = (votes / question_data['total_votes'] * 100) if question_data['total_votes'] > 0 else 0
                question_data['choices'].append({
                    'text': choice.choice_text,
                    'votes': votes,
                    'percentage': round(percentage, 2),
                    'is_correct': choice.is_correct
                })
            
            data['questions'].append(question_data)

        if format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="poll_{slug}_results.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Question', 'Choice', 'Votes', 'Percentage', 'Is Correct'])
            
            for question_data in data['questions']:
                for choice_data in question_data['choices']:
                    writer.writerow([
                        question_data['text'],
                        choice_data['text'],
                        choice_data['votes'],
                        f"{choice_data['percentage']}%",
                        'Yes' if choice_data['is_correct'] else 'No'
                    ])
            
            print(f"[INFO] Экспорт результатов опроса {slug} в CSV")
            return response
        else:
            # JSON экспорт с скачиванием
            from django.http import HttpResponse
            import json
            
            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="poll_{slug}_results.json"'
            
            print(f"[INFO] Экспорт результатов опроса {slug} в JSON")
            return response
    except Exception as e:
        print(f"[ERROR] Ошибка в export_results: {str(e)}")
        messages.error(request, f"Ошибка при экспорте результатов: {e}")
        return redirect('polls:list')


@login_required
def user_groups(request):
    if not request.user.is_staff:
        return redirect('home')
    
    groups = UserGroup.objects.all()
    
    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Group created successfully."))
            return redirect('polls:user_groups')
    else:
        form = UserGroupForm()
    
    return render(request, 'polls/user_groups.html', {
        'groups': groups,
        'form': form
    })


@login_required
def manage_poll_access(request, slug):
    try:
        poll = get_object_or_404(Poll, slug=slug)
        if request.user != poll.owner:
            print(f"[ERROR] Пользователь {request.user.username} не владелец опроса {slug}")
            return redirect('home')
        if request.method == 'POST':
            form = PollAccessForm(request.POST)
            if form.is_valid():
                access = form.save(commit=False)
                access.poll = poll
                access.save()
                messages.success(request, _("Access settings updated."))
                print(f"[INFO] Доступ к опросу {slug} обновлён")
                return redirect('polls:manage_access', slug=slug)
            else:
                print(f"[ERROR] Ошибки формы доступа: {form.errors}")
        else:
            form = PollAccessForm()
        access_list = poll.pollaccess_set.all()
        return render(request, 'polls/manage_access.html', {
            'poll': poll,
            'access_list': access_list,
            'form': form
        })
    except Exception as e:
        print(f"[ERROR] Ошибка в manage_poll_access: {str(e)}")
        messages.error(request, f"Ошибка при управлении доступом: {e}")
        return redirect('polls:list')


def share_poll(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    share_url = request.build_absolute_uri(poll.get_absolute_url())
    
    context = {
        'poll': poll,
        'share_url': share_url,
    }
    return render(request, 'polls/share_poll.html', context)


@csrf_exempt
def add_discussion_ajax(request, slug):
    if request.method == 'POST':
        poll = get_object_or_404(Poll, slug=slug)
        if not poll.allow_discussion:
            return JsonResponse({'error': 'Discussion not allowed for this poll'}, status=400)
        
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        discussion = Discussion.objects.create(
            poll=poll,
            user=request.user,
            message=message
        )
        
        return JsonResponse({
            'success': True,
            'discussion': {
                'id': discussion.id,
                'user': discussion.user.username,
                'message': discussion.message,
                'created_at': discussion.created_at.strftime('%d.%m.%Y %H:%M')
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def get_discussions_ajax(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    discussions = poll.discussion_set.all().order_by('-created_at')
    
    discussions_data = []
    for discussion in discussions:
        discussions_data.append({
            'id': discussion.id,
            'user': discussion.user.username,
            'message': discussion.message,
            'created_at': discussion.created_at.strftime('%d.%m.%Y %H:%M')
        })
    
    return JsonResponse({'discussions': discussions_data})


@login_required
def discussion(request, poll_id):
    # This is a stub, actual implementation needed
    poll = get_object_or_404(Poll, pk=poll_id)
    return render(request, 'polls/discussion.html', {'poll': poll})


@login_required
def post_comment(request, poll_id):
    # This is a stub, actual implementation needed
    return redirect('polls:discussion', poll_id=poll_id)


@login_required
def user_analytics(request):
    try:
        # Получаем все опросы пользователя
        user_polls = Poll.objects.filter(owner=request.user).order_by('-pub_date')
        
        # Общая статистика
        total_polls = user_polls.count()
        active_polls = user_polls.filter(active=True).count()
        total_votes = sum(poll.get_vote_count for poll in user_polls)
        
        # Статистика по типам опросов
        quiz_polls = user_polls.filter(is_quiz=True).count()
        multi_question_polls = user_polls.filter(is_multi_question=True).count()
        
        # Топ опросы по количеству голосов
        top_polls = sorted(user_polls, key=lambda x: x.get_vote_count, reverse=True)[:5]
        
        # Статистика по месяцам
        monthly_stats = user_polls.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Статистика голосования по месяцам
        monthly_votes = Vote.objects.filter(
            question__poll__owner=request.user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        context = {
            'total_polls': total_polls,
            'active_polls': active_polls,
            'total_votes': total_votes,
            'quiz_polls': quiz_polls,
            'multi_question_polls': multi_question_polls,
            'top_polls': top_polls,
            'monthly_stats': list(monthly_stats),
            'monthly_votes': list(monthly_votes),
        }
        
        print(f"[INFO] Общая аналитика пользователя отображена для {request.user.username}")
        return render(request, 'polls/user_analytics.html', context)
    except Exception as e:
        print(f"[ERROR] Ошибка в user_analytics: {str(e)}")
        messages.error(request, f"Ошибка при отображении аналитики: {e}")
        return redirect('polls:list_by_user')


@login_required
def export_user_data(request):
    try:
        format_type = request.GET.get('format', 'json')
        
        # Получаем все опросы пользователя
        user_polls = Poll.objects.filter(owner=request.user).order_by('-pub_date')
        
        # Подготавливаем данные для экспорта
        data = {
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'date_joined': request.user.date_joined.isoformat(),
            },
            'summary': {
                'total_polls': user_polls.count(),
                'active_polls': user_polls.filter(active=True).count(),
                'total_votes': sum(poll.get_vote_count for poll in user_polls),
                'quiz_polls': user_polls.filter(is_quiz=True).count(),
                'multi_question_polls': user_polls.filter(is_multi_question=True).count(),
            },
            'polls': []
        }
        
        # Добавляем данные по каждому опросу
        for poll in user_polls:
            poll_data = {
                'text': poll.text,
                'description': poll.description,
                'created_at': poll.created_at.isoformat(),
                'end_date': poll.end_date.isoformat() if poll.end_date else None,
                'active': poll.active,
                'is_quiz': poll.is_quiz,
                'is_multi_question': poll.is_multi_question,
                'total_votes': poll.get_vote_count,
                'questions': []
            }
            
            for question in poll.questions.all().order_by('order'):
                question_data = {
                    'text': question.text,
                    'order': question.order,
                    'total_votes': question.vote_set.count(),
                    'choices': []
                }
                
                for choice in question.choices.all().order_by('order'):
                    votes = choice.vote_set.count()
                    percentage = (votes / question_data['total_votes'] * 100) if question_data['total_votes'] > 0 else 0
                    question_data['choices'].append({
                        'text': choice.choice_text,
                        'votes': votes,
                        'percentage': round(percentage, 2),
                        'is_correct': choice.is_correct
                    })
                
                poll_data['questions'].append(question_data)
            
            data['polls'].append(poll_data)
        
        if format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="user_{request.user.username}_data.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Poll', 'Question', 'Choice', 'Votes', 'Percentage', 'Is Correct', 'Created', 'Status'])
            
            for poll_data in data['polls']:
                for question_data in poll_data['questions']:
                    for choice_data in question_data['choices']:
                        writer.writerow([
                            poll_data['text'],
                            question_data['text'],
                            choice_data['text'],
                            choice_data['votes'],
                            f"{choice_data['percentage']}%",
                            'Yes' if choice_data['is_correct'] else 'No',
                            poll_data['created_at'],
                            'Active' if poll_data['active'] else 'Ended'
                        ])
            
            print(f"[INFO] Экспорт данных пользователя {request.user.username} в CSV")
            return response
        else:
            # JSON экспорт с скачиванием
            from django.http import HttpResponse
            import json
            
            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="user_{request.user.username}_data.json"'
            
            print(f"[INFO] Экспорт данных пользователя {request.user.username} в JSON")
            return response
    except Exception as e:
        print(f"[ERROR] Ошибка в export_user_data: {str(e)}")
        messages.error(request, f"Ошибка при экспорте данных: {e}")
        return redirect('polls:list_by_user')


@login_required
def global_analytics(request):
    try:
        # Проверяем, является ли пользователь администратором
        if not request.user.is_staff:
            messages.error(request, "Доступ запрещен. Требуются права администратора.")
            return redirect('polls:list')
        
        # Общая статистика по системе
        total_polls = Poll.objects.count()
        active_polls = Poll.objects.filter(active=True).count()
        total_votes = Vote.objects.count()
        total_users = User.objects.count()
        
        # Статистика по типам опросов
        quiz_polls = Poll.objects.filter(is_quiz=True).count()
        multi_question_polls = Poll.objects.filter(is_multi_question=True).count()
        single_question_polls = total_polls - multi_question_polls
        
        # Топ пользователей по созданию опросов
        top_creators = User.objects.annotate(
            poll_count=Count('poll')
        ).filter(poll_count__gt=0).order_by('-poll_count')[:10]
        
        # Топ опросов по количеству голосов
        top_polls = Poll.objects.annotate(
            vote_count=Count('questions__vote')
        ).order_by('-vote_count')[:10]
        
        # Статистика по месяцам
        monthly_polls = Poll.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        monthly_votes = Vote.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Статистика активности пользователей
        active_voters = User.objects.annotate(
            vote_count=Count('vote')
        ).filter(vote_count__gt=0).order_by('-vote_count')[:10]
        
        # Статистика по дням недели
        from django.db.models.functions import ExtractDayOfWeek
        votes_by_day = Vote.objects.annotate(
            day_of_week=ExtractDayOfWeek('created_at')
        ).values('day_of_week').annotate(
            count=Count('id')
        ).order_by('day_of_week')
        
        # Статистика по часам
        from django.db.models.functions import ExtractHour
        votes_by_hour = Vote.objects.annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        context = {
            'total_polls': total_polls,
            'active_polls': active_polls,
            'total_votes': total_votes,
            'total_users': total_users,
            'quiz_polls': quiz_polls,
            'multi_question_polls': multi_question_polls,
            'single_question_polls': single_question_polls,
            'top_creators': top_creators,
            'top_polls': top_polls,
            'active_voters': active_voters,
            'monthly_polls': list(monthly_polls),
            'monthly_votes': list(monthly_votes),
            'votes_by_day': list(votes_by_day),
            'votes_by_hour': list(votes_by_hour),
        }
        
        print(f"[INFO] Глобальная аналитика отображена для администратора {request.user.username}")
        return render(request, 'polls/global_analytics.html', context)
    except Exception as e:
        print(f"[ERROR] Ошибка в global_analytics: {str(e)}")
        messages.error(request, f"Ошибка при отображении глобальной аналитики: {e}")
        return redirect('polls:list')


@login_required
def export_global_data(request):
    try:
        # Проверяем, является ли пользователь администратором
        if not request.user.is_staff:
            messages.error(request, "Доступ запрещен. Требуются права администратора.")
            return redirect('polls:list')
        
        format_type = request.GET.get('format', 'json')
        
        # Подготавливаем данные для экспорта
        data = {
            'summary': {
                'total_polls': Poll.objects.count(),
                'active_polls': Poll.objects.filter(active=True).count(),
                'total_votes': Vote.objects.count(),
                'total_users': User.objects.count(),
                'quiz_polls': Poll.objects.filter(is_quiz=True).count(),
                'multi_question_polls': Poll.objects.filter(is_multi_question=True).count(),
            },
            'top_polls': [],
            'top_users': [],
            'monthly_stats': []
        }
        
        # Топ опросов
        top_polls = Poll.objects.annotate(
            vote_count=Count('questions__vote')
        ).order_by('-vote_count')[:20]
        
        for poll in top_polls:
            data['top_polls'].append({
                'text': poll.text,
                'owner': poll.owner.username,
                'created_at': poll.created_at.isoformat(),
                'total_votes': poll.vote_count,
                'active': poll.active,
                'is_quiz': poll.is_quiz,
            })
        
        # Топ пользователей
        top_users = User.objects.annotate(
            poll_count=Count('poll'),
            vote_count=Count('vote')
        ).filter(poll_count__gt=0).order_by('-poll_count')[:20]
        
        for user in top_users:
            data['top_users'].append({
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined.isoformat(),
                'polls_created': user.poll_count,
                'votes_cast': user.vote_count,
            })
        
        # Месячная статистика
        monthly_stats = Poll.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            polls_count=Count('id'),
            votes_count=Count('questions__vote')
        ).order_by('month')
        
        for stat in monthly_stats:
            data['monthly_stats'].append({
                'month': stat['month'].isoformat(),
                'polls_created': stat['polls_count'],
                'votes_cast': stat['votes_count'],
            })
        
        if format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="global_analytics_{timezone.now().strftime("%Y%m%d")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Category', 'Metric', 'Value'])
            
            # Общая статистика
            writer.writerow(['Summary', 'Total Polls', data['summary']['total_polls']])
            writer.writerow(['Summary', 'Active Polls', data['summary']['active_polls']])
            writer.writerow(['Summary', 'Total Votes', data['summary']['total_votes']])
            writer.writerow(['Summary', 'Total Users', data['summary']['total_users']])
            writer.writerow(['Summary', 'Quiz Polls', data['summary']['quiz_polls']])
            writer.writerow(['Summary', 'Multi-Question Polls', data['summary']['multi_question_polls']])
            
            # Топ опросы
            for poll in data['top_polls']:
                writer.writerow(['Top Polls', poll['text'], f"{poll['total_votes']} votes"])
            
            # Топ пользователи
            for user in data['top_users']:
                writer.writerow(['Top Users', user['username'], f"{user['polls_created']} polls, {user['votes_cast']} votes"])
            
            print(f"[INFO] Экспорт глобальной аналитики в CSV")
            return response
        else:
            # JSON экспорт с скачиванием
            from django.http import HttpResponse
            import json
            
            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="global_analytics_{timezone.now().strftime("%Y%m%d")}.json"'
            
            print(f"[INFO] Экспорт глобальной аналитики в JSON")
            return response
    except Exception as e:
        print(f"[ERROR] Ошибка в export_global_data: {str(e)}")
        messages.error(request, f"Ошибка при экспорте глобальных данных: {e}")
        return redirect('polls:list')




