from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, PasswordResetToken

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'userprofile__user_type']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    def user_type(self, obj):
        try:
            return obj.userprofile.get_user_type_display()
        except:
            return _("Not set")
    user_type.short_description = _("User Type")

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['token', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# Перерегистрируем User модель
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
