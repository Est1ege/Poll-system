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
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.urls import reverse
from django import forms

from .models import Poll, Choice, Vote, PollInvitation, Discussion, UserGroup, PollAccess, Question
from .forms import PollAddForm, EditPollForm, ChoiceAddForm, PollInvitationForm, DiscussionForm, UserGroupForm, PollAccessForm, QuestionFormSet, ChoiceFormSet


@login_required
def poll_list(request):
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

    paginator = Paginator(all_polls, 6)
    page = request.GET.get('page')
    polls = paginator.get_page(page)

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'polls/polls_list.html', {
        'polls': polls,
        'params': params.urlencode(),
        'search_term': search_term,
    })


@login_required
def list_by_user(request):
    all_polls = Poll.objects.filter(owner=request.user).order_by('-pub_date')
    paginator = Paginator(all_polls, 7)
    page = request.GET.get('page')
    polls = paginator.get_page(page)
    return render(request, 'polls/polls_list.html', {'polls': polls})


@login_required
def poll_add(request):
    # Если нет права на добавление — показываем styled no_permission
    if not request.user.has_perm('polls.add_poll'):
        return render(request, 'polls/no_permission.html', status=403)

    if request.method == 'POST':
        form = PollAddForm(request.POST)
        question_formset = QuestionFormSet(request.POST, prefix='question_set')

        if form.is_valid():
            try:
                with transaction.atomic():
                    poll = form.save(commit=False)
                    poll.owner = request.user
                    poll.save()
                    
                    if poll.is_multi_question:
                        if question_formset.is_valid():
                            question_formset.instance = poll
                            questions = question_formset.save()
                            
                            # Более надежный способ сохранения вариантов ответов
                            for i, question in enumerate(questions):
                                choice_index = 0
                                while True:
                                    choice_text_key = f'choices_{i}-{choice_index}-choice_text'
                                    if choice_text_key not in request.POST or not request.POST[choice_text_key]:
                                        break # Прерываем, если нет следующего варианта ответа
                                    
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
                        else:
                            # Улучшенная обработка ошибок формсета
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
                        # Создаем один вопрос для обычного опроса
                        question = Question.objects.create(
                            poll=poll,
                            text=poll.text,
                            order=1,
                            is_required=True
                        )
                        
                        # Исправленная логика сохранения для обычного опроса
                        for i in range(1, 11):
                            choice_text = form.cleaned_data.get(f'choice{i}')
                            is_correct = form.cleaned_data.get(f'choice{i}_correct', False)
                            
                            if choice_text:  # Создаем выбор только если есть текст
                                Choice.objects.create(
                                    question=question,
                                    choice_text=choice_text,
                                    is_correct=is_correct,
                                    order=i
                                )
                
                messages.success(request, _("Poll & Choices added successfully."),
                                 extra_tags='alert alert-success')
                return redirect('polls:list')
            except forms.ValidationError as e:
                # Улучшенный вывод сообщения об ошибке
                error_message = " ".join(e.messages)
                messages.error(request, f"{error_message}", extra_tags='alert alert-danger')
            except Exception as e:
                messages.error(request, f"Error creating poll: {str(e)}",
                               extra_tags='alert alert-danger')
    else:
        form = PollAddForm()
        question_formset = QuestionFormSet(prefix='question_set', queryset=Question.objects.none())

    return render(request, 'polls/add_poll.html', {
        'form': form,
        'question_formset': question_formset,
    })


@login_required
def poll_edit(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')

    if request.method == 'POST':
        form = EditPollForm(request.POST, instance=poll)
        if form.is_valid():
            form.save()
            messages.success(request, _("Poll updated successfully."),
                             extra_tags='alert alert-success')
            return redirect('polls:list')
    else:
        form = EditPollForm(instance=poll)

    return render(request, 'polls/poll_edit.html', {'form': form, 'poll': poll})


@login_required
def poll_delete(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if poll.owner != request.user:
        messages.error(request, _("You do not have permission to delete this poll."))
        return redirect('polls:list')
    if request.method == 'POST':
        poll_text = poll.text
        poll.delete()
        messages.success(request, _("Poll '%(poll_text)s' has been deleted successfully.") % {'poll_text': poll_text})
        return redirect('polls:list')
    # Redirect GET requests
    return redirect('polls:detail', slug=slug)


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
    poll = get_object_or_404(Poll, slug=slug)
    if not poll.active:
        # если опрос закрыт — сразу перенаправляем на unified results
        return redirect('polls:results', slug=slug)
    
    first_question = poll.questions.first()
    choices = first_question.choices.all() if first_question else []
    
    return render(request, 'polls/poll_detail.html', {
        'poll': poll,
        'question': first_question,
        'choices': choices,
    })


@login_required
def poll_vote(request, slug):
    poll = get_object_or_404(Poll, slug=slug)

    if not poll.user_can_vote(request.user):
        return render(request, 'polls/already_voted.html', {'poll': poll})

    if request.method != 'POST':
        return redirect('polls:detail', slug=slug)

    choice_id = request.POST.get('choice')
    if not choice_id:
        messages.error(request, _("No choice selected!"),
                       extra_tags='alert alert-warning')
        return redirect('polls:detail', slug=slug)

    choice = get_object_or_404(Choice, pk=choice_id, question__poll=poll)
    question = choice.question

    try:
        Vote.objects.create(user=request.user, question=question, choice=choice)
    except IntegrityError:
        return render(request, 'polls/already_voted.html', {'poll': poll})

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
    poll = get_object_or_404(Poll, slug=slug)
    return render(request, 'polls/results.html', {'poll': poll})


@login_required
def poll_invite(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
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
            
            # Отправка email с приглашением
            subject = f"Приглашение на голосование: {poll.text}"
            message = render_to_string('polls/email/invitation.html', {
                'poll': poll,
                'invitation': invitation,
                'site_url': request.get_host()
            })
            
            send_mail(subject, message, 'noreply@example.com', [email])
            
            messages.success(request, _("Invitation sent successfully."))
            return redirect('polls:detail', slug=slug)
    else:
        form = PollInvitationForm()

    return render(request, 'polls/invite.html', {
        'form': form,
        'poll': poll
    })


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
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')

    # Статистика голосования
    total_votes = poll.get_vote_count
    choices_data = []
    
    first_question = poll.questions.first()
    if first_question:
        for choice in first_question.choices.all():
            votes = choice.get_vote_count
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            choices_data.append({
                'choice': choice.choice_text,
                'votes': votes,
                'percentage': round(percentage, 2)
            })

    # Временная статистика - needs adjustment for new structure
    votes_by_date = Vote.objects.filter(question__poll=poll).extra(
        select={'date': 'date(created_at)'}
    ).values('date').annotate(count=Count('id')).order_by('date')

    context = {
        'poll': poll,
        'total_votes': total_votes,
        'choices_data': choices_data,
        'votes_by_date': list(votes_by_date),
    }
    
    return render(request, 'polls/analytics.html', context)


@login_required
def export_results(request, slug):
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')

    format_type = request.GET.get('format', 'json')
    
    data = {
        'poll': {
            'text': poll.text,
            'description': poll.description,
            'created_at': poll.created_at.isoformat(),
            'end_date': poll.end_date.isoformat() if poll.end_date else None,
            'total_votes': poll.get_vote_count,
        },
        'choices': []
    }
    
    first_question = poll.questions.first()
    if first_question:
        for choice in first_question.choices.all():
            votes = choice.get_vote_count
            percentage = (votes / poll.get_vote_count * 100) if poll.get_vote_count > 0 else 0
            data['choices'].append({
                'text': choice.choice_text,
                'votes': votes,
                'percentage': round(percentage, 2)
            })

    if format_type == 'csv':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="poll_{slug}_results.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Choice', 'Votes', 'Percentage'])
        for choice_data in data['choices']:
            writer.writerow([choice_data['text'], choice_data['votes'], choice_data['percentage']])
        
        return response
    else:
        return JsonResponse(data)


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
    poll = get_object_or_404(Poll, slug=slug)
    if request.user != poll.owner:
        return redirect('home')
    
    if request.method == 'POST':
        form = PollAccessForm(request.POST)
        if form.is_valid():
            access = form.save(commit=False)
            access.poll = poll
            access.save()
            messages.success(request, _("Access settings updated."))
            return redirect('polls:manage_access', slug=slug)
    else:
        form = PollAccessForm()
    
    access_list = poll.pollaccess_set.all()
    
    return render(request, 'polls/manage_access.html', {
        'poll': poll,
        'access_list': access_list,
        'form': form
    })


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




