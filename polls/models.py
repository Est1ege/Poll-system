import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import secrets

class Poll(models.Model):
    VOTE_TYPES = [
        ('single', _('Single choice')),
        ('multiple', _('Multiple choice')),
        ('rating', _('Rating vote')),
    ]
    
    VISIBILITY_CHOICES = [
        ('anonymous', _('Anonymous')),
        ('public', _('Public')),
    ]
    
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Owner")
    )
    text = models.TextField(
        verbose_name=_("Question text")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    is_quiz = models.BooleanField(
        default=False,
        verbose_name=_("Is a quiz")
    )
    is_multi_question = models.BooleanField(
        default=False,
        verbose_name=_("Multiple questions poll")
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VOTE_TYPES,
        default='single',
        verbose_name=_("Vote type")
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='public',
        verbose_name=_("Vote visibility")
    )
    pub_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Publication date")
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("End date")
    )
    active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )
    allow_change_vote = models.BooleanField(
        default=True,
        verbose_name=_("Allow vote change")
    )
    show_results_before_end = models.BooleanField(
        default=False,
        verbose_name=_("Show results before end")
    )
    require_justification = models.BooleanField(
        default=False,
        verbose_name=_("Require justification")
    )
    allow_discussion = models.BooleanField(
        default=False,
        verbose_name=_("Allow discussion")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    slug = models.SlugField(
        max_length=36,
        unique=True,
        editable=False,
        default=uuid.uuid4,
        verbose_name=_("URL slug")
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = _("Poll")
        verbose_name_plural = _("Polls")

    def user_can_vote(self, user):
        if not user.is_authenticated:
            return False
        # This logic needs to be re-evaluated for multi-question polls
        # For now, this is a simplified check.
        return not Vote.objects.filter(question__poll=self, user=user).exists()

    def user_can_change_vote(self, user):
        if not self.allow_change_vote:
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return Vote.objects.filter(question__poll=self, user=user).exists()

    @property
    def is_expired(self):
        return self.end_date and timezone.now() > self.end_date

    @property
    def get_vote_count(self):
        return Vote.objects.filter(question__poll=self).count()

    def get_result_dict(self):
        res = []
        # Simplified logic for single-question polls
        first_question = self.questions.first()
        if not first_question:
            return []

        total = Vote.objects.filter(question=first_question).count()
        for choice in first_question.choices.all():
            num = choice.vote_set.count()
            res.append({
                'alert_class': secrets.choice(['primary', 'secondary', 'success', 'danger', 'dark', 'warning', 'info']),
                'text': choice.choice_text,
                'num_votes': num,
                'percentage': (num / total * 100) if total else 0
            })
        return res

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('polls:detail', kwargs={'slug': self.slug})

    def __str__(self):
        return f"{self.text[:50]}..."

class Question(models.Model):
    """Модель для вопросов в опросе с множественными вопросами"""
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_("Poll")
    )
    text = models.TextField(
        verbose_name=_("Question text")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name=_("Required")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        return f"{self.poll.text[:25]} - {self.text[:25]}"

class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name=_("Question")
    )
    choice_text = models.CharField(
        max_length=255,
        verbose_name=_("Choice text")
    )
    is_correct = models.BooleanField(
        default=False,
        verbose_name=_("Correct answer")
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = _("Choice")
        verbose_name_plural = _("Choices")

    def get_vote_count(self):
        return self.vote_set.count()

    def __str__(self):
        return f"{self.question.text[:25]} - {self.choice_text[:25]}"

class Vote(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name=_("Question")
    )
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        verbose_name=_("Choice")
    )
    justification = models.TextField(
        blank=True,
        verbose_name=_("Justification")
    )
    rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Rating")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at")
    )

    class Meta:
        unique_together = ('user', 'question')
        verbose_name = _("Vote")
        verbose_name_plural = _("Votes")

    def __str__(self):
        return f"{self.user.username} voted for {self.choice.choice_text} in {self.question.text}"

class PollInvitation(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        verbose_name=_("Poll")
    )
    email = models.EmailField(
        verbose_name=_("Email")
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Invitation token")
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_("Is used")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("Poll Invitation")
        verbose_name_plural = _("Poll Invitations")

    def __str__(self):
        return f"{self.poll.text[:30]}... - {self.email}"

class Discussion(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        verbose_name=_("Poll")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    message = models.TextField(
        verbose_name=_("Message")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Discussion")
        verbose_name_plural = _("Discussions")

    def __str__(self):
        return f"{self.poll.text[:30]}... - {self.user.username}"

class UserGroup(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name=_("Group name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    users = models.ManyToManyField(
        User,
        verbose_name=_("Users")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("User Group")
        verbose_name_plural = _("User Groups")

    def __str__(self):
        return self.name

class PollAccess(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        verbose_name=_("Poll")
    )
    user_group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("User group")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("User")
    )
    can_vote = models.BooleanField(
        default=True,
        verbose_name=_("Can vote")
    )
    can_view_results = models.BooleanField(
        default=True,
        verbose_name=_("Can view results")
    )

    class Meta:
        unique_together = [
            ('poll', 'user_group'),
            ('poll', 'user')
        ]
        verbose_name = _("Poll Access")
        verbose_name_plural = _("Poll Accesses")

    def __str__(self):
        if self.user_group:
            return f"{self.poll.text[:30]}... - {self.user_group.name}"
        return f"{self.poll.text[:30]}... - {self.user.username}"





