

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_super_admin', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    instance_id = models.UUIDField(null=True, blank=True)
    id = models.UUIDField(primary_key=True)
    aud = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    encrypted_password = models.CharField(max_length=255, null=True, blank=True)
    email_confirmed_at = models.DateTimeField(null=True, blank=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    confirmation_token = models.CharField(max_length=255, null=True, blank=True)
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    recovery_token = models.CharField(max_length=255, null=True, blank=True)
    recovery_sent_at = models.DateTimeField(null=True, blank=True)
    email_change_token_new = models.CharField(max_length=255, null=True, blank=True)
    email_change = models.CharField(max_length=255, null=True, blank=True)
    email_change_sent_at = models.DateTimeField(null=True, blank=True)
    last_sign_in_at = models.DateTimeField(null=True, blank=True)
    raw_app_meta_data = models.JSONField(null=True, blank=True)
    raw_user_meta_data = models.JSONField(null=True, blank=True)
    is_super_admin = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    phone = models.TextField(null=True, blank=True)
    phone_confirmed_at = models.DateTimeField(null=True, blank=True)
    phone_change = models.TextField(null=True, blank=True)
    phone_change_token = models.CharField(max_length=255, null=True, blank=True)
    phone_change_sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    email_change_token_current = models.CharField(max_length=255, null=True, blank=True)
    email_change_confirm_status = models.SmallIntegerField(null=True, blank=True)
    banned_until = models.DateTimeField(null=True, blank=True)
    reauthentication_token = models.CharField(max_length=255, null=True, blank=True)
    reauthentication_sent_at = models.DateTimeField(null=True, blank=True)
    is_sso_user = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    password = None 
    last_login = None

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        managed = False
        db_table = 'auth\".\"users'

    def __str__(self):
        return self.email or str(self.id)

    @property
    def is_staff(self):
        return self.is_super_admin

    @property
    def is_superuser(self):
        return self.is_super_admin

    @property
    def is_active(self):
        return self.confirmed_at is not None and self.banned_until is None

    def has_perm(self, perm, obj=None):
        return self.is_super_admin

    def has_module_perms(self, app_label):
        return self.is_super_admin

    def set_password(self, raw_password):
        # This method is required by Django, but we don't want to set the password here
        pass

    def check_password(self, raw_password):
        # This method is required by Django, but we'll always return False
        # as we're not storing or checking passwords in Django
        return False

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        managed = True

    def __str__(self):
        return f"Profile of {self.user.email}"

    @classmethod
    def create_for_user(cls, user):
        return cls.objects.create(user=user)