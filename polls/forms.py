from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy
from .models import Poll, Choice, Discussion, PollInvitation, UserGroup, PollAccess, Question


class PollAddForm(forms.ModelForm):
    
    class Meta:
        model = Poll
        fields = ['text', 'description', 'is_quiz', 'is_multi_question', 'end_date', 'allow_discussion']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Enter your question here...')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Optional description...')}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_quiz': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is-quiz'}),
            'is_multi_question': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is-multi-question'}),
            'allow_discussion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, 11):
            self.fields[f'choice{i}'] = forms.CharField(
                max_length=255,
                required=False, # We'll validate in clean()
                label=format_lazy(_('Choice {}'), i),
                widget=forms.TextInput(attrs={'class': 'form-control choice-field'})
            )
            self.fields[f'choice{i}_correct'] = forms.BooleanField(
                required=False,
                label=_("Correct answer"),
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input correct-field'})
            )

    def clean(self):
        cleaned_data = super().clean()
        is_quiz = cleaned_data.get('is_quiz')
        is_multi_question = cleaned_data.get('is_multi_question')
        
        if not is_multi_question:
            choices_provided_indices = []
            for i in range(1, 11):
                if cleaned_data.get(f'choice{i}'):
                    choices_provided_indices.append(i)
            
            if len(choices_provided_indices) < 2:
                # Add a non-field error
                raise forms.ValidationError(
                    _("You must provide at least two answer choices."),
                    code='not_enough_choices'
                )

            if is_quiz:
                correct_answers = 0
                for i in choices_provided_indices:
                    if cleaned_data.get(f'choice{i}_correct'):
                        correct_answers += 1
                
                if correct_answers == 0:
                    raise forms.ValidationError(
                        _("For a quiz, you must select at least one correct answer from the ones you provided."),
                        code='no_correct_answer'
                    )
        
        return cleaned_data


class MultiQuestionPollForm(forms.ModelForm):
    """Форма для создания опросов с множественными вопросами"""
    num_questions = forms.IntegerField(
        min_value=2,
        max_value=20,
        initial=3,
        label=_("Number of questions"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'num-questions'})
    )
    
    class Meta:
        model = Poll
        fields = ['text', 'description', 'is_quiz', 'end_date', 'allow_discussion']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Enter poll title...')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Optional description...')}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_quiz': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'is-quiz'}),
            'allow_discussion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuestionForm(forms.ModelForm):
    """Форма для создания вопросов"""
    class Meta:
        model = Question
        fields = ['text', 'order', 'is_required']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EditPollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['text', 'description', 'is_quiz', 'end_date', 'allow_discussion']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_quiz': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_discussion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ChoiceAddForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'order']
        widgets = {
            'choice_text': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class VoteForm(forms.Form):
    choice = forms.ModelChoiceField(
        queryset=Choice.objects.none(),
        widget=forms.RadioSelect,
        label=_("Your choice")
    )
    justification = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label=_("Justification (optional)")
    )
    rating = forms.IntegerField(
        min_value=1,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label=_("Rating (1-10)")
    )

    def __init__(self, poll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['choice'].queryset = poll.choice_set.all()
        if not poll.require_justification:
            self.fields['justification'].required = False
        if poll.vote_type != 'rating':
            del self.fields['rating']


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PollInvitationForm(forms.ModelForm):
    class Meta:
        model = PollInvitation
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PollAccessForm(forms.ModelForm):
    class Meta:
        model = PollAccess
        fields = ['user_group', 'user', 'can_vote', 'can_view_results']
        widgets = {
            'can_vote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view_results': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text', 'is_correct', 'order']
        widgets = {
            'choice_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


# Formset для вопросов
QuestionFormSet = inlineformset_factory(
    Poll, Question,
    form=QuestionForm,
    extra=1,
    can_delete=True,
    fields=['text', 'order', 'is_required']
)

# Formset для вариантов ответов (будет использоваться для каждого вопроса)
ChoiceFormSet = inlineformset_factory(
    Question, Choice,
    form=ChoiceForm,
    extra=2,
    can_delete=True,
    fields=['choice_text', 'is_correct', 'order']
)



