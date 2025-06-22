from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    Poll, Choice, Vote, PollInvitation, Discussion, 
    UserGroup, PollAccess, Question
)

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['text', 'order', 'is_required']

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1
    fields = ['choice_text', 'is_correct', 'order']

class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['user', 'choice', 'justification', 'rating', 'created_at']

class PollInvitationInline(admin.TabularInline):
    model = PollInvitation
    extra = 1
    readonly_fields = ['token', 'is_used', 'created_at']

class DiscussionInline(admin.TabularInline):
    model = Discussion
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'message', 'created_at']

class PollAccessInline(admin.TabularInline):
    model = PollAccess
    extra = 1
    fields = ['user_group', 'user', 'can_vote', 'can_view_results']

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = [
        'text_short', 'owner', 'vote_type', 'visibility', 
        'active', 'pub_date', 'end_date', 'vote_count', 
        'is_expired_display'
    ]
    list_filter = [
        'active', 'vote_type', 'visibility', 'is_quiz', 'is_multi_question',
        'allow_change_vote', 'show_results_before_end',
        'require_justification', 'allow_discussion',
        'created_at', 'pub_date'
    ]
    search_fields = ['text', 'description', 'owner__username', 'owner__email']
    date_hierarchy = 'pub_date'
    readonly_fields = ['slug', 'created_at', 'vote_count', 'is_expired']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('text', 'description', 'owner', 'slug')
        }),
        (_('Vote Settings'), {
            'fields': (
                'vote_type', 'visibility', 'is_quiz', 'is_multi_question',
                'allow_change_vote', 'show_results_before_end',
                'require_justification', 'allow_discussion'
            )
        }),
        (_('Timing'), {
            'fields': ('pub_date', 'end_date', 'active')
        }),
        (_('Statistics'), {
            'fields': ('vote_count', 'is_expired'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [QuestionInline, PollInvitationInline, DiscussionInline, PollAccessInline]
    
    actions = ['activate_polls', 'deactivate_polls', 'export_results']
    
    def text_short(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_short.short_description = _("Question")
    
    def vote_count(self, obj):
        return obj.get_vote_count
    vote_count.short_description = _("Votes")
    
    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">{}</span>', _("Expired"))
        return format_html('<span style="color: green;">{}</span>', _("Active"))
    is_expired_display.short_description = _("Status")
    
    def activate_polls(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} polls activated.")
    activate_polls.short_description = _("Activate selected polls")
    
    def deactivate_polls(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} polls deactivated.")
    deactivate_polls.short_description = _("Deactivate selected polls")
    
    def export_results(self, request, queryset):
        # Здесь можно добавить экспорт результатов
        pass
    export_results.short_description = _("Export results")

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'poll', 'order', 'is_required', 'choice_count', 'created_at']
    list_filter = ['is_required', 'created_at', 'poll__active']
    search_fields = ['text', 'poll__text']
    autocomplete_fields = ['poll']
    readonly_fields = ['choice_count']
    
    def text_short(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_short.short_description = _("Question")
    
    def choice_count(self, obj):
        return obj.choices.count()
    choice_count.short_description = _("Choices")

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['choice_text', 'question', 'is_correct', 'vote_count', 'order', 'created_at']
    list_filter = ['is_correct', 'created_at', 'question__poll__active']
    search_fields = ['choice_text', 'question__text']
    autocomplete_fields = ['question']
    readonly_fields = ['vote_count']
    
    def vote_count(self, obj):
        return obj.get_vote_count
    vote_count.short_description = _("Votes")

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'choice', 'rating', 'created_at']
    list_filter = ['created_at', 'question__poll__active', 'question__poll__vote_type']
    search_fields = ['user__username', 'question__text', 'choice__choice_text', 'justification']
    autocomplete_fields = ['user', 'question', 'choice']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Vote Information'), {
            'fields': ('user', 'question', 'choice')
        }),
        (_('Additional Data'), {
            'fields': ('justification', 'rating'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PollInvitation)
class PollInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'poll', 'is_used', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email', 'poll__text']
    readonly_fields = ['token', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('poll')

@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ['user', 'poll', 'message_short', 'created_at']
    list_filter = ['created_at', 'poll__active']
    search_fields = ['user__username', 'poll__text', 'message']
    readonly_fields = ['created_at']
    
    def message_short(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_short.short_description = _("Message")

@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_count', 'description_short', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['users']
    readonly_fields = ['created_at']
    
    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = _("Users")
    
    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_short.short_description = _("Description")

@admin.register(PollAccess)
class PollAccessAdmin(admin.ModelAdmin):
    list_display = ['poll', 'user_group', 'user', 'can_vote', 'can_view_results']
    list_filter = ['can_vote', 'can_view_results', 'poll__active']
    search_fields = ['poll__text', 'user_group__name', 'user__username']
    autocomplete_fields = ['poll', 'user_group', 'user']
