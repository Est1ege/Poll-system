from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class PollMeAdminSite(AdminSite):
    site_header = _("PollMe Beauty - Администрирование")
    site_title = _("PollMe Beauty")
    index_title = _("Панель управления системой голосования")
    site_url = '/'

admin_site = PollMeAdminSite(name='pollme_admin') 