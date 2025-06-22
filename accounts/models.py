from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Create your models here.

class UserProfile(models.Model):
    USER_TYPES = [
        ('student', _('Student')),
        ('teacher', _('Teacher')),
        ('employee', _('Employee')),
        ('admin', _('Administrator')),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPES,
        default='student',
        verbose_name=_("User type")
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone number")
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Department")
    )
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Position")
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name=_("Avatar")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User")
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("Reset token")
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_("Is used")
    )
    expires_at = models.DateTimeField(
        verbose_name=_("Expires at")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at")
    )

    class Meta:
        verbose_name = _("Password Reset Token")
        verbose_name_plural = _("Password Reset Tokens")

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"
