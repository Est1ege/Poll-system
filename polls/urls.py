from django.urls import path
from . import views

app_name = 'polls'

urlpatterns = [
    path('', views.poll_list, name='list'),
    path('add/', views.poll_add, name='add'),
    path('user/', views.list_by_user, name='list_by_user'),
    path('user/analytics/', views.user_analytics, name='user_analytics'),
    path('user/export/', views.export_user_data, name='export_user_data'),
    path('global/analytics/', views.global_analytics, name='global_analytics'),
    path('global/export/', views.export_global_data, name='export_global_data'),
    path('groups/', views.user_groups, name='user_groups'),
    path('choice/<int:choice_id>/edit/', views.choice_edit, name='choice_edit'),
    path('choice/<int:choice_id>/delete/', views.choice_delete, name='choice_delete'),
    path('access/<slug:slug>/', views.manage_poll_access, name='manage_access'),
    path('discussion/<slug:slug>/add/', views.add_discussion_ajax, name='add_discussion_ajax'),
    path('discussion/<slug:slug>/get/', views.get_discussions_ajax, name='get_discussions_ajax'),
    path('<slug:slug>/', views.poll_detail, name='detail'),
    path('<slug:slug>/vote/', views.poll_vote, name='vote'),
    path('<slug:slug>/results/', views.results_view, name='results'),
    path('<slug:slug>/edit/choice/add/', views.add_choice, name='add_choice'),
    path('<slug:slug>/end_poll/', views.end_poll, name='end_poll'),
    path('<slug:slug>/invite/', views.poll_invite, name='invite'),
    path('<slug:slug>/analytics/', views.poll_analytics, name='analytics'),
    path('<slug:slug>/export/', views.export_results, name='export'),
    path('<slug:slug>/share/', views.share_poll, name='share'),
    path('<slug:slug>/edit/', views.poll_edit, name='edit'),
    path('<slug:slug>/delete/', views.poll_delete, name='delete'),
    path('<int:poll_id>/discussion/', views.discussion, name='discussion'),
    path('<int:poll_id>/discussion/post/', views.post_comment, name='post_comment'),
]
