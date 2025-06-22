from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
import csv
import json
from datetime import datetime

def export_poll_results_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="poll_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Poll', 'Choice', 'Votes', 'Percentage', 'Created Date'])
    
    for poll in queryset:
        total_votes = poll.get_vote_count
        for choice in poll.choice_set.all():
            votes = choice.get_vote_count
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            writer.writerow([
                poll.text[:50],
                choice.choice_text,
                votes,
                f"{percentage:.2f}%",
                poll.created_at.strftime("%Y-%m-%d %H:%M")
            ])
    
    return response
export_poll_results_csv.short_description = _("Export results to CSV")

def export_poll_results_json(modeladmin, request, queryset):
    data = []
    
    for poll in queryset:
        poll_data = {
            'poll': {
                'text': poll.text,
                'description': poll.description,
                'created_at': poll.created_at.isoformat(),
                'end_date': poll.end_date.isoformat() if poll.end_date else None,
                'total_votes': poll.get_vote_count,
            },
            'choices': []
        }
        
        for choice in poll.choice_set.all():
            votes = choice.get_vote_count
            percentage = (votes / poll.get_vote_count * 100) if poll.get_vote_count > 0 else 0
            poll_data['choices'].append({
                'text': choice.choice_text,
                'votes': votes,
                'percentage': round(percentage, 2)
            })
        
        data.append(poll_data)
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="poll_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
    
    return response
export_poll_results_json.short_description = _("Export results to JSON")

def send_invitations(modeladmin, request, queryset):
    # Здесь можно добавить логику отправки приглашений
    pass
send_invitations.short_description = _("Send invitations to selected polls")

def generate_analytics_report(modeladmin, request, queryset):
    # Здесь можно добавить генерацию аналитического отчета
    pass
generate_analytics_report.short_description = _("Generate analytics report") 